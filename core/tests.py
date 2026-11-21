from django.test import TestCase

from .forms import ClaimForm, ReportForm
from .models import Category, Item, Location


class ReportFormCategoryTests(TestCase):
    def test_category_field_has_standardized_options_and_placeholder(self):
        form = ReportForm()

        self.assertEqual(form.fields['category'].choices[0], ('', 'Select any'))
        self.assertEqual(
            [value for value, _ in form.fields['category'].choices if value],
            [
                'Electronics',
                'Documents',
                'Jewelry & Valuables',
                'Stationery & Books',
                'Personal Belongings',
                'Others',
            ],
        )

        rendered = form.fields['category'].widget.render('category', '')
        self.assertIn('value=""', rendered)
        self.assertIn('disabled', rendered)

    def test_blank_category_is_rejected(self):
        form = ReportForm(
            data={
                'item_name': 'Phone',
                'category': '',
                'report_type': 'LOST',
                'description': 'A test description',
                'location': 'Library',
                'date_lost_found': '2024-01-01',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)


class BrowseItemsViewTests(TestCase):
    def setUp(self):
        self.electronics = Category.objects.create(category_name='Electronics')
        self.stationery = Category.objects.create(category_name='Stationery & Books')
        self.location = Location.objects.create(building='Library')
        Item.objects.create(name='USB Drive', category=self.electronics, description='A small flash drive', status='FOUND', location=self.location)
        Item.objects.create(name='Notebook', category=self.stationery, description='A spiral notebook', status='LOST', location=self.location)

    def test_items_page_filters_by_category_and_shows_summary(self):
        response = self.client.get('/items/', {'category': self.electronics.category_id, 'sort': 'recent'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'USB Drive')
        self.assertNotContains(response, 'Notebook')
        self.assertContains(response, 'Showing 1 item')


class ClaimFormTests(TestCase):
    def setUp(self):
        category = Category.objects.create(category_name='Electronics')
        location = Location.objects.create(building='Library')
        self.item = Item.objects.create(name='Phone', category=category, description='Black phone', status='FOUND', location=location)

    def test_claim_form_requires_verification_fields(self):
        form = ClaimForm(item=self.item, data={
            'claimant_name': 'Ada Lovelace',
            'claimant_email': 'ada@example.com',
            'claimant_phone': '1234567890',
            'ownership_description': 'I bought this phone in 2023.',
            'declaration_confirmed': True,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('identity_proof', form.errors)
        self.assertIn('ownership_proof', form.errors)

    def test_claim_form_accepts_preselected_item(self):
        form = ClaimForm(item=self.item, data={
            'claimant_name': 'Ada Lovelace',
            'claimant_email': 'ada@example.com',
            'claimant_phone': '1234567890',
            'ownership_description': 'I bought this phone in 2023.',
            'declaration_confirmed': True,
        })

        self.assertEqual(form.fields['item'].initial, self.item.item_id)
