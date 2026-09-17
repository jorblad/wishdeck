<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 560px; max-width: 92vw">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ t('bulkImport.title') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="close" />
      </q-card-section>

      <q-card-section>
        <q-select
          v-model="categoryId"
          :options="categoryOptions"
          :label="t('bulkImport.category')"
          dense
          outlined
          emit-value
          map-options
          clearable
          class="q-mb-sm"
        />
        <q-input
          v-model="text"
          :label="t('bulkImport.textLabel')"
          type="textarea"
          rows="10"
          dense
          outlined
          autogrow
        />

        <q-separator class="q-my-md" />

        <div class="text-caption q-mb-xs">{{ t('bulkImport.htmlHint') }}</div>
        <q-input
          type="textarea"
          rows="3"
          dense
          outlined
          :placeholder="t('bulkImport.htmlPlaceholder')"
          @paste.prevent="onHtmlPaste"
        />

        <q-toggle
          v-model="scrape"
          :label="t('bulkImport.scrape')"
          class="q-mt-sm"
        />
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('common.cancel')" @click="close" />
        <q-btn
          color="primary"
          :label="t('bulkImport.import')"
          :loading="loading"
          :disable="!text.trim()"
          @click="submit"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  wishlistId: { type: String, default: '' },
  categories: { type: Array, default: () => [] },
});
const emit = defineEmits(['update:modelValue', 'imported']);

const { t } = useI18n();
const $q = useQuasar();

const text = ref('');
const categoryId = ref(null);
const loading = ref(false);
const htmlExtracting = ref(false);
const scrape = ref(false);

const categoryOptions = computed(() =>
  props.categories.map((c) => ({ label: c.name, value: c.id }))
);

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      text.value = '';
      categoryId.value = null;
      scrape.value = false;
    }
  }
);

function close() {
  emit('update:modelValue', false);
}

function appendExtracted(links) {
  const lines = links
    .map((link) => {
      const title = (link.title || '').trim();
      return title ? `${title} - ${link.url}` : link.url;
    })
    .filter(Boolean);
  if (!lines.length) return;
  const prefix = text.value.trim() ? `${text.value.trim()}\n` : '';
  text.value = prefix + lines.join('\n');
}

async function onHtmlPaste(event) {
  const html = event.clipboardData?.getData('text/html') || '';
  const plain = event.clipboardData?.getData('text/plain') || '';
  if (!html.trim() && !plain.trim()) return;
  const payload = html.trim() ? { html: html.trim() } : { text: plain.trim() };
  htmlExtracting.value = true;
  try {
    const { data } = await api.post('/utils/extract-links', payload);
    if (data.length) {
      appendExtracted(data);
      $q.notify({
        type: 'positive',
        message: t('bulkImport.extracted', { count: data.length }),
      });
    } else {
      $q.notify({
        type: 'warning',
        message: t('bulkImport.noLinksFound'),
      });
    }
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.response?.data?.detail || t('bulkImport.extractFailed'),
    });
  } finally {
    htmlExtracting.value = false;
  }
}

async function submit() {
  if (!text.value.trim()) return;
  loading.value = true;
  try {
    const { data } = await api.post(`/wishlists/${props.wishlistId}/items/bulk`, {
      text: text.value,
      category_id: categoryId.value || null,
      scrape: scrape.value,
    });
    emit('imported', data.items);
    $q.notify({
      type: 'positive',
      message: t('bulkImport.imported', { count: data.created }),
    });
    close();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.response?.data?.detail || t('bulkImport.failed'),
    });
  } finally {
    loading.value = false;
  }
}
</script>
