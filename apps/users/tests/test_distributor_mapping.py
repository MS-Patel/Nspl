import pytest
from django.urls import reverse
from apps.users.models import User, InvestorProfile, DistributorProfile, RMProfile, Branch
from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(username="admin", password="password", user_type=User.Types.ADMIN)
    return user

@pytest.fixture
def rm_user(db):
    user = User.objects.create_user(username="rm1", password="password", user_type=User.Types.RM)
    branch = Branch.objects.create(name="Branch A", code="BR-A")
    RMProfile.objects.create(user=user, branch=branch, employee_code="EMP001")
    return user

@pytest.fixture
def distributor_user(db):
    user = User.objects.create_user(username="dist1", password="password", user_type=User.Types.DISTRIBUTOR)
    return user

@pytest.fixture
def rm_distributor(db, rm_user):
    user = User.objects.create_user(username="dist_rm", password="password", user_type=User.Types.DISTRIBUTOR)
    dist = DistributorProfile.objects.create(user=user, arn_number="ARN-RM1", rm=rm_user.rm_profile, pan="ABCDE1234J")
    return dist

@pytest.fixture
def other_distributor(db):
    user = User.objects.create_user(username="dist_other", password="password", user_type=User.Types.DISTRIBUTOR)
    dist = DistributorProfile.objects.create(user=user, arn_number="ARN-OTHER")
    return dist

@pytest.fixture
def investor_unmapped(db):
    user = User.objects.create_user(username="inv_unmapped", password="password", user_type=User.Types.INVESTOR)
    inv = InvestorProfile.objects.create(user=user, pan="ABCDE1234F", kyc_status=True)
    return inv

@pytest.fixture
def investor_rm_owned(db, rm_distributor, rm_user):
    user = User.objects.create_user(username="inv_rm", password="password", user_type=User.Types.INVESTOR)
    # Investor is mapped to RM via Distributor
    inv = InvestorProfile.objects.create(user=user, pan="ABCDE1234G", kyc_status=True, distributor=rm_distributor, rm=rm_user.rm_profile)
    return inv

@pytest.fixture
def investor_other_owned(db, other_distributor):
    user = User.objects.create_user(username="inv_other", password="password", user_type=User.Types.INVESTOR)
    inv = InvestorProfile.objects.create(user=user, pan="ABCDE1234H", kyc_status=True, distributor=other_distributor)
    return inv


@pytest.mark.django_db
class TestDistributorMapping:

    def test_access_control(self, client, admin_user, rm_user, distributor_user):
        url = reverse('users:distributor_mapping')

        # Admin - OK
        client.force_login(admin_user)
        resp = client.get(url)
        assert resp.status_code == 200

        # RM - OK
        client.force_login(rm_user)
        resp = client.get(url)
        assert resp.status_code == 200

        # Distributor - Forbidden
        client.force_login(distributor_user)
        resp = client.get(url)
        assert resp.status_code == 403

    def test_admin_manual_mapping(self, client, admin_user, investor_unmapped, rm_distributor):
        client.force_login(admin_user)
        url = reverse('users:distributor_mapping')

        data = {
            'action': 'assign_selected',
            'investor_ids': str(investor_unmapped.id),
            'distributor_id': rm_distributor.id
        }

        resp = client.post(url, data, follow=True)
        assert resp.status_code == 200

        investor_unmapped.refresh_from_db()
        assert investor_unmapped.distributor == rm_distributor
        assert investor_unmapped.rm == rm_distributor.rm
        assert investor_unmapped.branch == rm_distributor.rm.branch

    def test_rm_manual_mapping_own_investor(self, client, rm_user, investor_rm_owned, rm_distributor):
        # RM tries to unassign (Direct) their own investor
        client.force_login(rm_user)
        url = reverse('users:distributor_mapping')

        data = {
            'action': 'assign_selected',
            'investor_ids': str(investor_rm_owned.id),
            'distributor_id': '' # Unassign
        }

        resp = client.post(url, data, follow=True)
        assert resp.status_code == 200

        investor_rm_owned.refresh_from_db()
        assert investor_rm_owned.distributor is None
        # Should still be mapped to RM (Direct)
        assert investor_rm_owned.rm == rm_user.rm_profile

    def test_rm_cannot_map_others_investor(self, client, rm_user, investor_other_owned, rm_distributor):
        client.force_login(rm_user)
        url = reverse('users:distributor_mapping')

        data = {
            'action': 'assign_selected',
            'investor_ids': str(investor_other_owned.id),
            'distributor_id': rm_distributor.id
        }

        resp = client.post(url, data, follow=True)

        investor_other_owned.refresh_from_db()
        # Should NOT change
        assert investor_other_owned.distributor != rm_distributor

    def test_csv_upload_admin(self, client, admin_user, investor_unmapped, rm_distributor):
        client.force_login(admin_user)
        url = reverse('users:distributor_mapping')

        csv_content = f"investor_pan,distributor_pan\n{investor_unmapped.pan},{rm_distributor.pan}"
        csv_file = SimpleUploadedFile("mapping.csv", csv_content.encode('utf-8'), content_type="text/csv")

        data = {
            'action': 'upload_csv',
            'csv_file': csv_file
        }

        resp = client.post(url, data, follow=True)
        assert resp.status_code == 200

        investor_unmapped.refresh_from_db()
        assert investor_unmapped.distributor == rm_distributor
