import json
import re
import os
from uuid import uuid4

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.views import View 
from django.views.decorators.http import require_http_methods
from django import forms
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import DefaultStorage
from django.core.exceptions import PermissionDenied

from .models import UPVOTE, DOWNVOTE, FLAG
from .models import Post, Comment, Vote, User, PostWithCustomGet, CommentWithCustomGet
from .models import update_gchat_space
from charcha.teams.models import Team

regex = re.compile(r"<h[1-6]>([^<^>]+)</h[1-6]>")
def prepare_html_for_edit(html):
    'Converts all heading tags to h1 because trix only understands h1 tags'
    return re.sub(regex, r"<h1>\1</h1>", html)    

@login_required
def homepage(request):
    posts = Post.objects.recent_posts_with_my_votes(request.user)
    teams = Team.objects.my_teams(request.user)
    return render(request, "home.html", context={"posts": posts, "teams": teams})

@login_required
def team_home(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    active_members = team.active_team_members()
    posts = Post.objects.posts_in_team_with_my_votes(request.user, team=team)
    return render(request, "home.html", context={"posts": posts, "team": team, "active_members": active_members})

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['html']
        labels = {
            'html': 'Your Comment',
        }
        widgets = {'html': forms.HiddenInput()}

class DiscussionView(LoginRequiredMixin, View):
    def get(self, request, post_id):
        post = Post.objects.get_post_with_my_votes(post_id, 
                    request.user)
        comments = Comment.objects.best_ones_first(post, 
                        request.user)
        form = CommentForm()
        context = {"post": post, "comments": comments, "form": form}
        return render(request, "discussion.html", context=context)

    def post(self, request, post_id):
        post = Post.objects.get_post_with_my_votes(post_id, 
                    request.user)
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = post.add_comment(form.cleaned_data['html'], request.user)
            post_url = reverse('discussion', args=[post.id])
            return HttpResponseRedirect(post_url)
        else:
            context = {"post": post, "form": form, "comments": []}
            return render(request, "discussion.html", context=context)

class ReplyToComment(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        parent_comment = get_object_or_404(CommentWithCustomGet, pk=kwargs['id'], requester=request.user)
        post = parent_comment.post
        form = CommentForm()
        context = {"post": post, "parent_comment": parent_comment, "form": form}
        return render(request, "reply-to-comment.html", context=context)

    def post(self, request, **kwargs):
        parent_comment = get_object_or_404(CommentWithCustomGet, pk=kwargs['id'], requester=request.user)
        form = CommentForm(request.POST)

        if not form.is_valid():
            post = parent_comment.post
            context = {"post": post, "parent_comment": parent_comment, "form": form}
            return render(request, "reply-to-comment.html", context=context)

        comment = parent_comment.reply(form.cleaned_data['html'], request.user)
        post_url = reverse('discussion', args=[parent_comment.post.id])
        return HttpResponseRedirect(post_url)

class EditComment(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        comment = get_object_or_404(CommentWithCustomGet, pk=kwargs['id'], requester=request.user)
        comment.html = prepare_html_for_edit(comment.html)
        form = CommentForm(instance=comment)
        context = {"form": form}
        return render(request, "edit-comment.html", context=context)

    def post(self, request, **kwargs):
        comment = get_object_or_404(CommentWithCustomGet, pk=kwargs['id'], requester=request.user)
        form = CommentForm(request.POST, instance=comment)

        if not form.is_valid():
            context = {"form": form}
            return render(request, "edit-comment.html", context=context)
        else:
            comment.edit_comment(form.cleaned_data['html'], request.user)
        post_url = reverse('discussion', args=[comment.post.id])
        return HttpResponseRedirect(post_url)

class TeamSelect(forms.SelectMultiple):
    '''Renders a many-to-many field as a single select dropdown
        While the backend supports many-to-many relationship,
        we are not yet ready to expose it to users yet.
        So we mask the multiple select field into a single select
    '''
    def render(self, *args, **kwargs):
        rendered = super().render(*args, **kwargs)
        return rendered.replace('multiple>\n', '>\n')
        
class StartDiscussionForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['teams', 'title', 'html']
        labels = {
            'teams': 'Teams',
            'title': 'Title',
            'html': 'Details'
        }
        widgets = {
            'html': forms.HiddenInput(),
            'teams': TeamSelect()}

    def clean(self):
        cleaned_data = super(StartDiscussionForm, self).clean()
        html = cleaned_data.get("html")
        if not html:
            raise forms.ValidationError(
                "HTML cannot be empty"
            )
        return cleaned_data

class StartDiscussionView(LoginRequiredMixin, View):
    def team_choices(self, user):
        teams = Team.objects.my_teams(user)
        return [(team.id, team.name) for team in teams]

    def get(self, request):
        form = StartDiscussionForm(initial={"author": request.user})
        form.fields['teams'].choices = self.team_choices(request.user)
        return render(request, "submit.html", context={"form": form})

    def post(self, request):
        form = StartDiscussionForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            teams = form.cleaned_data["teams"]
            post = Post.objects.new_post(request.user, post, teams)
            new_post_url = reverse('discussion', args=[post.id])
            return HttpResponseRedirect(new_post_url)
        else:
            form.fields['teams'].choices = self.team_choices(request.user)
            return render(request, "submit.html", context={"form": form})

class EditDiscussionForm(StartDiscussionForm):
    class Meta:
        model = Post
        fields = ['title', 'html']
        widgets = {'html': forms.HiddenInput()}

class EditDiscussion(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        post = get_object_or_404(PostWithCustomGet, pk=kwargs['post_id'], requester=request.user)
        post.html = prepare_html_for_edit(post.html)
        form = EditDiscussionForm(instance=post)
        context = {"form": form}
        return render(request, "edit-discussion.html", context=context)

    def post(self, request, **kwargs):
        post = get_object_or_404(PostWithCustomGet, pk=kwargs['post_id'], requester=request.user)
        form = EditDiscussionForm(request.POST, instance=post)

        if not form.is_valid():
            context = {"form": form}
            return render(request, "edit-discussion.html", context=context)
        else:
            post.edit_post(form.cleaned_data['title'], form.cleaned_data['html'], request.user)
        post_url = reverse('discussion', args=[post.id])
        return HttpResponseRedirect(post_url)

@login_required
@require_http_methods(['POST'])
def upvote_post(request, post_id):
    post = get_object_or_404(PostWithCustomGet, pk=post_id, requester=request.user)
    post.upvote(request.user)
    post.refresh_from_db()
    return HttpResponse(post.upvotes)

@login_required
@require_http_methods(['POST'])
def downvote_post(request, post_id):
    post = get_object_or_404(PostWithCustomGet, pk=post_id, requester=request.user)
    post.downvote(request.user)
    post.refresh_from_db()
    return HttpResponse(post.downvotes)

@login_required
@require_http_methods(['POST'])
def upvote_comment(request, comment_id):
    comment = get_object_or_404(CommentWithCustomGet, pk=comment_id, requester=request.user)
    comment.upvote(request.user)
    comment.refresh_from_db()
    return HttpResponse(comment.upvotes)

@login_required
@require_http_methods(['POST'])
def downvote_comment(request, comment_id):
    comment = get_object_or_404(CommentWithCustomGet, pk=comment_id, requester=request.user)
    comment.downvote(request.user)
    comment.refresh_from_db()
    return HttpResponse(comment.downvotes)

@login_required
def myprofile(request):
    return render(request, "profile.html", context={"user": request.user })

@login_required
def profile(request, userid):
    user = get_object_or_404(User, id=userid)
    return render(request, "profile.html", context={"user": user })

class FileUploadView(LoginRequiredMixin, View):
    def post(self, request, **kwargs):
        file_obj = request.FILES.get('file')
        filename = request.POST['key']
        extension = filename.split(".")[-1].lower()
        if extension not in ('png', 'jpeg', 'jpg', 'svg', 'gif'):
            return HttpResponseBadRequest("Files of type " + extension + " are not supported")
        
        # TODO: Add validation here e.g. file size/type check
        # TODO: Potentially resize image

        # organize a path for the file in bucket
        file_path = '{uuid}/{userid}.{extension}'.\
            format(userid=request.user.id, 
            uuid=uuid4(), extension=extension)
        
        media_storage = DefaultStorage()
        media_storage.save(file_path, file_obj)
        file_url = media_storage.url(file_path)

        # The file url contains a signature, which expires in a few hours
        # In our case, we have made the S3 file public for anyone who has the url
        # Which means, the file is accessible without the signature
        # So we simply strip out the signature from the url - i.e. everything after the ?

        file_url = file_url.split('?')[0]
        
        return JsonResponse({
            'message': 'OK',
            'fileUrl': file_url,
        })