from django.test import TestCase
from django.contrib.auth.models import User
from landing.models import Community, CommunityJoinRequest, Member, Event
from django.utils import timezone

class CommunityModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.community = Community.objects.create(name='Test Community', description='Test description', creator=self.user, tags='test')

    def test_community_creation(self):
        self.assertEqual(self.community.name, 'Test Community')
        self.assertEqual(self.community.creator, self.user)

class CommunityJoinRequestModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.community = Community.objects.create(name='Test Community', description='Test description', creator=self.user, tags='test')
        self.join_request = CommunityJoinRequest.objects.create(user=self.user, community=self.community)

    def test_join_request(self):
        self.assertEqual(self.join_request.user, self.user)
        self.assertEqual(self.join_request.community, self.community)
        self.assertEqual(self.join_request.status, 'pending')

class MemberModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.community = Community.objects.create(name='Test Community', description='Test description', creator=self.user, tags='test')
        self.member = Member.objects.create(user=self.user, community=self.community)

    def test_member_creation(self):
        self.assertEqual(self.member.user, self.user)
        self.assertEqual(self.member.community, self.community)

class EventModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.community = Community.objects.create(name='Test Community', description='Test description', creator=self.user, tags='test')
        self.event = Event.objects.create(name='Test Event', date=timezone.now(), description='Test event description', event_type='social', location='Test location', community=self.community, creator=self.user)

    def test_event_creation(self):
        self.assertEqual(self.event.name, 'Test Event')
        self.assertEqual(self.event.community, self.community)
        self.assertEqual(self.event.creator, self.user)
