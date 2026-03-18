from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from landing.models import Community, CommunityJoinRequest, Member

class CommunityViewsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.community = Community.objects.create(name='Test Community', description='Test description', creator=self.user, tags='test')
        self.client.login(username='testuser', password='testpass123')

    def test_landing_page(self):
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Community")

    def test_join_community(self):
        response = self.client.post(reverse('join_community', args=[self.community.id]))
        self.assertEqual(response.status_code, 302)  # Redirects after joining

        join_request = CommunityJoinRequest.objects.filter(user=self.user, community=self.community)
        self.assertTrue(join_request.exists())

    def test_community_detail_access(self):
        # Create a non-member user
        non_member = User.objects.create_user(username='nonmember', password='testpass123')
        self.client.login(username='nonmember', password='testpass123')
        
        # Try to access community detail
        response = self.client.get(reverse('community_detail', args=[self.community.id]))
        
        # Should return forbidden status
        self.assertEqual(response.status_code, 403)

class RequestViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.community = Community.objects.create(name='Test Community', description='Test description', creator=self.user, tags='test')
        self.client.login(username='testuser', password='12345')

    def test_handle_join_request(self):
        join_request = CommunityJoinRequest.objects.create(user=self.user, community=self.community)

        response = self.client.post(reverse('handle_join_request', args=[join_request.id, 'accept']))
        self.assertEqual(response.status_code, 302)  # Redirect after handling

        join_request.refresh_from_db()
        self.assertEqual(join_request.status, 'accepted')
