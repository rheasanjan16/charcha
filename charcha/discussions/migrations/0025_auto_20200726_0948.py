# Generated by Django 3.0.7 on 2020-07-26 09:48

from django.conf import settings
import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion

def create_roles_and_permissions(apps, schema_editor):
    Role = apps.get_model("discussions", "Role")
    Permission = apps.get_model("discussions", "Permission")

    administrator = Role.objects.create(name="administrator")
    moderator = Role.objects.create(name="moderator")
    member = Role.objects.create(name="member")
    guest = Role.objects.create(name="guest")

SOFT_DELETE_ALL_PARENT_COMMENTS = """
    UPDATE comments as c
    SET is_deleted = true
    WHERE exists (
        SELECT 'x' FROM posts p where p.temp_comment_id = c.id
    )
"""

UPDATE_GCHAT_KEY_IN_USER = """
    UPDATE users as u
    SET gchat_primary_key = gu.key
    FROM gchat_users as gu
    WHERE gu.user_id = u.id
"""

MIGRATE_TEAMS_TO_GROUPS = """
    INSERT INTO groups(name, group_type, purpose, description, is_deleted, emails)
    SELECT name, 1, description, about, false, array[]::varchar[] FROM TEAMS
"""

MIGRATE_TEAM_MEMBERS_TO_GROUP_MEMBERS = """
    INSERT INTO group_members(group_id, user_id, role_id)
    SELECT g.id, u.id, 3
    FROM team_members tm JOIN teams t on tm.team_id = t.id
        JOIN groups g on g.name = t.name
        JOIN gchat_users gu on tm.gchat_user_id = gu.id
        JOIN users u on gu.user_id = u.id
"""

MIGRATE_TEAM_TO_GCHAT_SPACES = """
    INSERT INTO gchat_spaces(name, space, is_deleted)
    SELECT name, gchat_space, false FROM teams
"""

MIGRATE_TEAM_TO_GROUP_GCHAT_SPACES = """
    INSERT INTO group_gchat_spaces(group_id, gchat_space_id, notify, sync_members)
    SELECT g.id, gs.id, true, true
    FROM teams t JOIN groups g on t.name = g.name
    JOIN gchat_spaces gs on t.name = gs.name
"""

UPDATE_POSTS_SET_GROUP = """
    UPDATE posts as p
    SET group_id = g.id
    FROM groups g, teams t, team_posts tp
    WHERE p.id = tp.post_id AND tp.team_id = t.id
    AND t.name = g.name
"""

UPDATE_POSTS_SET_GROUP_FOR_CHILD_POSTS = """
    UPDATE posts as child
    SET group_id = parent.group_id
    FROM posts parent 
    WHERE child.parent_post_id = parent.id
"""

SUBSCRIBE_AUTHORS = """
    INSERT INTO post_subscriptions(post_id, user_id, notify_on)
    SELECT p1.id, p1.author_id, 2
    FROM posts p1 
    WHERE p1.parent_post_id is null
    UNION ALL
    SELECT p2.parent_post_id, p2.author_id, 1
    FROM posts p2
    WHERE p2.parent_post_id is not null
"""

MIGRATE_VOTES_TO_REACTIONS = """
    INSERT INTO reactions(post_id, author_id, reaction, submission_time)
    SELECT v.object_id, v.voter_id, 
        CASE v.type_of_vote WHEN 1 THEN '👍' WHEN 2 THEN '👎' END, 
        v.submission_time
    FROM votes v
    WHERE v.content_type_id = 8;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('discussions', '0024_comments_to_posts'),
    ]

    operations = [
        migrations.CreateModel(
            name='GchatSpace',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('space', models.CharField(max_length=50)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'gchat_spaces',
            },
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the group', max_length=100)),
                ('group_type', models.IntegerField(choices=[(0, 'Open'), (1, 'Closed'), (2, 'Secret')], help_text="Closed groups can be seen on the listing page and request an invitation, but only members can see the posts. Secret groups don't show up on the listing page.")),
                ('is_deleted', models.BooleanField(default=False)),
                ('purpose', models.CharField(help_text='A 1 or 2 sentence explaining the purpose of this group', max_length=200)),
                ('description', models.TextField(help_text='A larger description that can contain links, charter or any other text to better describe the group', max_length=4096)),
                ('emails', django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254), help_text='Mailing list address for this group', size=8)),
            ],
            options={
                'db_table': 'groups',
            },
        ),
        migrations.CreateModel(
            name='GroupGchatSpace',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notify', models.BooleanField(default=True, help_text='Notify the chat room whenever a new post is created in this charcha group')),
                ('sync_members', models.BooleanField(default=True, help_text='Automatically sync chat room members with this charcha group')),
                ('gchat_space', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.GchatSpace', verbose_name='Room Name')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Group')),
            ],
            options={
                'verbose_name': 'Chat Room',
                'db_table': 'group_gchat_spaces',
            },
        ),
        migrations.CreateModel(
            name='GroupMember',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Group')),
            ],
            options={
                'db_table': 'group_members',
            },
        ),
        migrations.CreateModel(
            name='LastSeenOnPost',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seen', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'last_seen_on_post',
            },
        ),
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
                ('description', models.CharField(max_length=200)),
            ],
            options={
                'db_table': 'permissions',
            },
        ),
        migrations.CreateModel(
            name='PostMembers',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'post_members',
            },
        ),
        migrations.CreateModel(
            name='PostSubscribtion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notify_on', models.IntegerField(choices=[(0, 'Mute'), (1, 'Replies Only'), (2, 'New Posts and Replies Only'), (3, 'All Notifications')])),
            ],
            options={
                'db_table': 'post_subscriptions',
            },
        ),
        migrations.CreateModel(
            name='PostTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tagged_on', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'post_tags',
            },
        ),
        migrations.CreateModel(
            name='Reaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reaction', models.CharField(max_length=1)),
                ('submission_time', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'reactions',
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
            ],
            options={
                'db_table': 'roles',
            },
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Permission')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Role')),
            ],
            options={
                'db_table': 'role_permissions',
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('fqn', models.CharField(max_length=200)),
                ('is_external', models.BooleanField(default=False)),
                ('imported_on', models.DateTimeField(default=None, null=True)),
                ('ext_id', models.CharField(max_length=40, null=True)),
                ('ext_link', models.URLField(blank=True, null=True)),
                ('is_visible', models.BooleanField(default=True)),
                ('attributes', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('parent', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to='discussions.Tag')),
            ],
            options={
                'db_table': 'tags',
            },
        ),
        migrations.AddField(
            model_name='comment',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='comment',
            name='last_modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='favourite',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='favourite',
            name='post',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='discussions.Post'),
        ),
        migrations.AddField(
            model_name='post',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='post',
            name='last_activity',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='post',
            name='last_modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='post',
            name='reaction_summary',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='post',
            name='score',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='band',
            field=models.CharField(default=None, max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='designation',
            field=models.CharField(default=None, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='employee_id',
            field=models.CharField(default=None, max_length=4, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='gchat_primary_key',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='joining_date',
            field=models.DateField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='tzname',
            field=models.CharField(default='Asia/Kolkata', max_length=50),
        ),
        migrations.AlterField(
            model_name='comment',
            name='html',
            field=models.TextField(max_length=256),
        ),
        migrations.AlterField(
            model_name='post',
            name='html',
            field=models.TextField(max_length=16384),
        ),
        migrations.AlterField(
            model_name='post',
            name='parent_post',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to='discussions.Post'),
        ),
        migrations.AlterField(
            model_name='post',
            name='slug',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AlterField(
            model_name='post',
            name='title',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='gchat_space',
            field=models.CharField(blank=True, default=None, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='role',
            name='permissions',
            field=models.ManyToManyField(related_name='roles', through='discussions.RolePermission', to='discussions.Permission'),
        ),
        migrations.AddField(
            model_name='reaction',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='reaction',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='reactions', to='discussions.Post'),
        ),
        migrations.AddField(
            model_name='posttag',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Post'),
        ),
        migrations.AddField(
            model_name='posttag',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Tag'),
        ),
        migrations.AddField(
            model_name='postsubscribtion',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Post'),
        ),
        migrations.AddField(
            model_name='postsubscribtion',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='postmembers',
            name='member',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='postmembers',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Group'),
        ),
        migrations.AddField(
            model_name='lastseenonpost',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Post'),
        ),
        migrations.AddField(
            model_name='lastseenonpost',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='groupmember',
            name='role',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='discussions.Role'),
        ),
        migrations.AddField(
            model_name='groupmember',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='group',
            name='gchat_spaces',
            field=models.ManyToManyField(help_text='Associate this group to one or more gchat rooms. This has two purposes - 1) to automatically import members from the gchat room, and 2) to notify the gchat room when a new post is added', through='discussions.GroupGchatSpace', to='discussions.GchatSpace', verbose_name='Google chat rooms associated with this group'),
        ),
        migrations.AddField(
            model_name='group',
            name='members',
            field=models.ManyToManyField(help_text='Members of this group', related_name='mygroups', through='discussions.GroupMember', to=settings.AUTH_USER_MODEL, verbose_name='Members of this group'),
        ),
        migrations.AddField(
            model_name='post',
            name='group',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='discussions.Group'),
        ),
        migrations.AddField(
            model_name='post',
            name='last_seen',
            field=models.ManyToManyField(related_name='last_seen', through='discussions.LastSeenOnPost', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='post',
            name='subscriptions',
            field=models.ManyToManyField(blank=True, related_name='subscriptions', through='discussions.PostSubscribtion', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='post',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='posts', through='discussions.PostTag', to='discussions.Tag'),
        ),
        migrations.AddIndex(
            model_name='tag',
            index=models.Index(fields=['ext_id'], name='tags_ext_id_4900b3_idx'),
        ),
        migrations.AddIndex(
            model_name='tag',
            index=models.Index(fields=['name'], name='tags_name_38920e_idx'),
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(fields=('parent', 'name'), name='tag_unique_name_within_parent'),
        ),
        migrations.AlterIndexTogether(
            name='reaction',
            index_together={('post', 'author')},
        ),
        migrations.AddIndex(
            model_name='lastseenonpost',
            index=models.Index(fields=['user', 'post'], name='lastseenonpostindx_user_post'),
        ),
        migrations.AddConstraint(
            model_name='lastseenonpost',
            constraint=models.UniqueConstraint(fields=('user', 'post'), name='lastseenonpost_unique_user_post'),
        ),
                migrations.AlterIndexTogether(
            name='vote',
            index_together=None,
        ),
        migrations.RunSQL(SOFT_DELETE_ALL_PARENT_COMMENTS),
        migrations.RunPython(create_roles_and_permissions),
        migrations.RunSQL(UPDATE_GCHAT_KEY_IN_USER),
        migrations.RunSQL(MIGRATE_TEAMS_TO_GROUPS),
        migrations.RunSQL(MIGRATE_TEAM_MEMBERS_TO_GROUP_MEMBERS),
        migrations.RunSQL(MIGRATE_TEAM_TO_GCHAT_SPACES),
        migrations.RunSQL(MIGRATE_TEAM_TO_GROUP_GCHAT_SPACES),
        migrations.RunSQL(UPDATE_POSTS_SET_GROUP),
        migrations.RunSQL(UPDATE_POSTS_SET_GROUP_FOR_CHILD_POSTS),
        migrations.RunSQL(SUBSCRIBE_AUTHORS),
        migrations.RunSQL(MIGRATE_VOTES_TO_REACTIONS),
        migrations.RemoveField(
            model_name='vote',
            name='content_type',
        ),
        migrations.RemoveField(
            model_name='vote',
            name='voter',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='downvotes',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='flags',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='parent_comment',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='upvotes',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='wbs',
        ),
        migrations.RemoveField(
            model_name='favourite',
            name='content_type',
        ),
        migrations.RemoveField(
            model_name='favourite',
            name='deleted_on',
        ),
        migrations.RemoveField(
            model_name='favourite',
            name='object_id',
        ),
        migrations.RemoveField(
            model_name='post',
            name='downvotes',
        ),
        migrations.RemoveField(
            model_name='post',
            name='flags',
        ),
        migrations.RemoveField(
            model_name='post',
            name='temp_comment_id',
        ),
        migrations.RemoveField(
            model_name='post',
            name='upvotes',
        ),
        migrations.DeleteModel(
            name='TeamPosts',
        ),
        migrations.DeleteModel(
            name='Vote',
        ),
    ]
