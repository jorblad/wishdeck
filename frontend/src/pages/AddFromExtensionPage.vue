<template>
  <q-page class="q-pa-md" style="max-width: 640px; margin: 0 auto">
    <div class="text-h5 q-mb-md">{{ t('addFromExtension.title') }}</div>
    <q-banner v-if="fromExtension" class="bg-info text-white q-mb-md rounded-borders">
      {{ t('addFromExtension.autoCloseHint') }}
    </q-banner>

    <q-card>
      <q-card-section>
        <q-select
          v-model="wishlistId"
          :options="wishlistOptions"
          :label="t('addFromExtension.wishlist')"
          dense
          outlined
          emit-value
          map-options
          class="q-mb-sm"
        />

        <q-select
          v-model="categoryId"
          :options="categoryOptions"
          :label="t('addFromExtension.category')"
          dense
          outlined
          emit-value
          map-options
          clearable
          class="q-mb-sm"
        />

        <q-input v-model="form.title" :label="t('addFromExtension.titleField')" dense outlined class="q-mb-sm" />
        <q-input
          v-model="form.description"
          :label="t('addFromExtension.description')"
          type="textarea"
          autogrow
          dense
          outlined
          class="q-mb-sm"
        />
        <q-input v-model="form.url" :label="t('addFromExtension.url')" dense outlined class="q-mb-sm" />
        <q-input v-model="form.image_url" :label="t('addFromExtension.image')" dense outlined class="q-mb-sm" />

        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-6">
            <q-input
              v-model.number="form.price"
              :label="t('addFromExtension.price')"
              type="number"
              dense
              outlined
              clearable
            />
          </div>
          <div class="col-6">
            <q-input v-model="form.currency" :label="t('addFromExtension.currency')" dense outlined />
          </div>
        </div>

        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-6">
            <q-input v-model.number="form.priority" :label="t('addFromExtension.priority')" type="number" dense outlined />
          </div>
          <div class="col-6">
            <q-input
              v-model.number="form.quantity"
              :label="t('addFromExtension.quantity')"
              type="number"
              dense
              outlined
              clearable
              :hint="t('addFromExtension.quantityHint')"
            />
          </div>
        </div>

        <q-btn
          color="secondary"
          icon="auto_awesome"
          :label="t('addFromExtension.scrape')"
          :loading="scraping"
          :disable="!form.url"
          class="q-mr-sm"
          @click="scrape"
        />
        <q-btn
          color="primary"
          icon="save"
          :label="t('addFromExtension.save')"
          :loading="saving"
          :disable="!wishlistId || !form.title"
          @click="submit"
        />
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const $q = useQuasar();

const wishlists = ref([]);
const wishlistId = ref(null);
const categoryId = ref(null);
const loadingWishlists = ref(true);
const scraping = ref(false);
const saving = ref(false);

const form = reactive({
  title: '',
  description: '',
  url: '',
  image_url: '',
  price: null,
  currency: '',
  priority: 0,
  quantity: 1,
});

const wishlistOptions = computed(() =>
  wishlists.value.map((w) => ({ label: w.title, value: w.id }))
);

const categoryOptions = computed(() => {
  const wl = wishlists.value.find((w) => w.id === wishlistId.value);
  return (wl?.categories || []).map((c) => ({ label: c.name, value: c.id }));
});

watch(
  () => wishlistId.value,
  () => {
    categoryId.value = null;
  }
);

onMounted(async () => {
  const queryUrl = route.query.url || '';
  const queryTitle = route.query.title || '';
  form.url = typeof queryUrl === 'string' ? queryUrl : '';
  form.title = typeof queryTitle === 'string' ? queryTitle : '';

  try {
    const { data } = await api.get('/wishlists');
    wishlists.value = data;
    if (data.length === 1) {
      wishlistId.value = data[0].id;
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: t('addFromExtension.loadWishlistsFailed') });
  } finally {
    loadingWishlists.value = false;
  }
});

async function scrape() {
  if (!form.url) return;
  scraping.value = true;
  try {
    const { data } = await api.post('/utils/scrape-link', { url: form.url });
    form.title = data.title || form.title;
    form.description = data.description || form.description;
    form.image_url = data.image_url || form.image_url;
    form.price = data.price ?? form.price;
    form.currency = data.currency || form.currency;
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.response?.data?.detail || t('addFromExtension.scrapeFailed'),
    });
  } finally {
    scraping.value = false;
  }
}

const fromExtension = computed(() => route.query.source === 'extension');

async function submit() {
  if (!wishlistId.value || !form.title) return;
  saving.value = true;
  try {
    await api.post(`/wishlists/${wishlistId.value}/items`, {
      title: form.title,
      description: form.description || null,
      url: form.url || null,
      image_url: form.image_url || null,
      price: form.price === '' ? null : form.price,
      currency: form.currency || null,
      category_id: categoryId.value || null,
      priority: form.priority,
      quantity: form.quantity === '' ? null : form.quantity,
    });
    $q.notify({ type: 'positive', message: t('addFromExtension.saved') });
    if (fromExtension.value) {
      setTimeout(() => {
        window.close();
      }, 1200);
    } else {
      router.push(`/wishlists/owner/${wishlistId.value}`);
    }
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.response?.data?.detail || t('addFromExtension.saveFailed'),
    });
  } finally {
    saving.value = false;
  }
}
</script>
