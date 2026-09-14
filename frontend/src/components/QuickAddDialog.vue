<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 480px; max-width: 92vw">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ t('quickAdd.title') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="close" />
      </q-card-section>

      <q-card-section>
        <!-- Step 1: paste a URL and auto-scrape -->
        <div class="row q-col-gutter-sm items-end">
          <div class="col">
            <q-input
              v-model="url"
              :label="t('quickAdd.url')"
              dense
              outlined
              :disable="scraping"
              @keyup.enter="scrape"
            />
          </div>
          <div class="col-auto">
            <q-btn
              color="secondary"
              icon="auto_awesome"
              :label="t('quickAdd.scrape')"
              :loading="scraping"
              @click="scrape"
            />
          </div>
        </div>

        <q-separator class="q-my-md" />

        <!-- Step 2: editable fields -->
        <q-input v-model="title" :label="t('quickAdd.titleField')" dense outlined class="q-mb-sm" />
        <q-input
          v-model="description"
          :label="t('quickAdd.description')"
          dense
          outlined
          type="textarea"
          autogrow
          class="q-mb-sm"
        />
        <div class="row q-col-gutter-sm">
          <div class="col-8">
            <q-input v-model="imageUrl" :label="t('quickAdd.image')" dense outlined />
          </div>
          <div class="col-4">
            <q-input v-model="currency" :label="t('quickAdd.currency')" dense outlined />
          </div>
        </div>
        <div class="row q-col-gutter-sm q-mt-xs">
          <div class="col-6">
            <q-input v-model.number="price" :label="t('quickAdd.price')" type="number" dense outlined />
          </div>
          <div class="col-6">
            <q-select
              v-model="categoryId"
              :options="categoryOptions"
              :label="t('quickAdd.category')"
              dense
              outlined
              emit-value
              map-options
              clearable
              use-input
              hide-selected
              fill-input
              input-debounce="0"
              @new-value="createCategory"
            />
          </div>
        </div>
        <div class="row q-col-gutter-sm q-mt-xs">
          <div class="col-6">
            <q-input v-model.number="priority" :label="t('quickAdd.priority')" type="number" dense outlined />
          </div>
          <div class="col-6">
            <q-input v-model.number="quantity" :label="t('quickAdd.quantity')" type="number" dense outlined />
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('common.cancel')" @click="close" />
        <q-btn
          color="primary"
          :label="t('quickAdd.add')"
          :loading="saving"
          :disable="!title"
          @click="submit"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from 'boot/axios';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  wishlistId: { type: String, default: '' },
  categories: { type: Array, default: () => [] },
});
const emit = defineEmits(['update:modelValue', 'added', 'category-created']);

const { t } = useI18n();

const url = ref('');
const title = ref('');
const description = ref('');
const imageUrl = ref('');
const currency = ref('');
const price = ref(null);
const categoryId = ref(null);
const priority = ref(0);
const quantity = ref(1);
const scraping = ref(false);
const saving = ref(false);

const categoryOptions = computed(() =>
  props.categories.map((c) => ({ label: c.name, value: c.id }))
);

watch(
  () => props.modelValue,
  (open) => {
    if (open) reset();
  }
);

function reset() {
  url.value = '';
  title.value = '';
  description.value = '';
  imageUrl.value = '';
  currency.value = '';
  price.value = null;
  categoryId.value = null;
  priority.value = 0;
  quantity.value = 1;
}

function close() {
  emit('update:modelValue', false);
}

async function createCategory(name, done) {
  const trimmed = (name || '').trim();
  done();
  if (!trimmed) return;
  try {
    const { data } = await api.post(`/wishlists/${props.wishlistId}/categories`, {
      name: trimmed,
    });
    emit('category-created', data);
    categoryId.value = data.id;
  } catch (e) {
    // If creation failed, ignore — the user can retry or pick an existing one.
    console.error(e);
  }
}

async function scrape() {
  if (!url.value) return;
  scraping.value = true;
  try {
    const { data } = await api.post('/utils/scrape-link', { url: url.value });
    title.value = data.title || title.value;
    description.value = data.description || description.value;
    imageUrl.value = data.image_url || imageUrl.value;
    price.value = data.price ?? price.value;
    currency.value = data.currency || currency.value;
  } catch (e) {
    // ignore — user can still fill manually
    console.error(e);
  } finally {
    scraping.value = false;
  }
}

async function submit() {
  saving.value = true;
  try {
    const { data } = await api.post(`/wishlists/${props.wishlistId}/items`, {
      title: title.value,
      description: description.value || null,
      url: url.value || null,
      image_url: imageUrl.value || null,
      currency: currency.value || null,
      price: price.value ?? null,
      category_id: categoryId.value || null,
      priority: priority.value,
      quantity: quantity.value,
    });
    emit('added', data);
    close();
  } catch (e) {
    console.error(e);
  } finally {
    saving.value = false;
  }
}
</script>
