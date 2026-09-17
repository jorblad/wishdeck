<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 520px; max-width: 92vw">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ isOwner ? t('item.editTitle') : t('item.details') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="close" />
      </q-card-section>

      <q-card-section v-if="item">
        <q-img
          v-if="item.image_url"
          :src="item.image_url"
          spinner-color="primary"
          style="max-height: 180px"
          class="rounded-borders q-mb-md"
        />

        <template v-if="isOwner">
          <q-input v-model="form.title" :label="t('item.title')" dense outlined class="q-mb-sm" />
          <q-input
            v-model="form.description"
            :label="t('item.description')"
            dense
            outlined
            type="textarea"
            autogrow
            class="q-mb-sm"
          />
          <q-input v-model="form.url" :label="t('item.link')" dense outlined class="q-mb-sm" />
          <q-input v-model="form.image_url" :label="t('item.image')" dense outlined class="q-mb-sm" />
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-6">
              <q-input
                v-model.number="form.price"
                :label="t('item.price')"
                type="number"
                dense
                outlined
                clearable
              />
            </div>
            <div class="col-6">
              <q-input v-model="form.currency" :label="t('item.currency')" dense outlined />
            </div>
          </div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-6">
              <q-select
                v-model="form.category_id"
                :options="categoryOptions"
                :label="t('item.category')"
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
            <div class="col-3">
              <q-input v-model.number="form.priority" :label="t('item.priority')" type="number" dense outlined />
            </div>
            <div class="col-3">
              <q-input
                v-model.number="form.quantity"
                :label="t('item.quantity')"
                type="number"
                dense
                outlined
                clearable
                :hint="t('item.quantityHint')"
              />
            </div>
          </div>
        </template>

        <template v-else>
          <div class="text-h6 q-mb-xs">{{ item.title }}</div>
          <div v-if="item.description" class="text-body2 q-mb-sm">{{ item.description }}</div>
          <div v-if="item.price != null" class="text-subtitle1 q-mb-sm">
            {{ item.price }} {{ item.currency || '' }}
          </div>
          <div v-if="item.quantity != null" class="text-caption q-mb-sm">
            {{ t('item.quantityLabel') }}: {{ item.quantity }}
          </div>
          <div v-if="item.categoryName" class="text-caption q-mb-sm">{{ item.categoryName }}</div>
          <q-chip v-if="allowClaims && item.status" :color="statusColor(item.status)" text-color="white" class="q-mb-md">
            {{ t('wishlist.status.' + item.status) }}
          </q-chip>
          <div v-if="item.url" class="q-mt-sm">
            <q-btn
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
              color="primary"
              size="sm"
              icon="open_in_new"
              :label="t('item.openLink')"
            />
          </div>
          <div v-else class="text-grey q-mt-sm">{{ t('item.noLink') }}</div>
        </template>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('common.cancel')" @click="close" />
        <template v-if="isOwner">
          <q-btn
            flat
            color="negative"
            :label="t('item.delete')"
            @click="remove"
          />
          <q-btn
            flat
            color="warning"
            :label="t('item.archive')"
            @click="archive"
          />
          <q-btn
            color="primary"
            :label="t('common.save')"
            :loading="saving"
            :disable="!form.title"
            @click="submit"
          />
        </template>
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  item: { type: Object, default: null },
  isOwner: { type: Boolean, default: false },
  allowClaims: { type: Boolean, default: true },
  categories: { type: Array, default: () => [] },
});
const emit = defineEmits(['update:modelValue', 'saved', 'deleted', 'archived', 'category-created']);

const { t } = useI18n();
const $q = useQuasar();

const saving = ref(false);
const form = reactive({
  id: null,
  title: '',
  description: '',
  url: '',
  image_url: '',
  price: null,
  currency: '',
  category_id: null,
  priority: 0,
  quantity: 1,
});

const categoryOptions = computed(() =>
  props.categories.map((c) => ({ label: c.name, value: c.id }))
);

watch(
  () => props.modelValue,
  (open) => {
    if (open && props.item) {
      form.id = props.item.id;
      form.title = props.item.title || '';
      form.description = props.item.description || '';
      form.url = props.item.url || '';
      form.image_url = props.item.image_url || '';
      form.price = props.item.price ?? null;
      form.currency = props.item.currency || '';
      form.category_id = props.item.category_id || null;
      form.priority = props.item.priority ?? 0;
      form.quantity = props.item.quantity ?? null;
    }
  }
);

function statusColor(status) {
  if (status === 'claimed') return 'orange';
  if (status === 'purchased') return 'green';
  return 'grey';
}

function close() {
  emit('update:modelValue', false);
}

async function createCategory(name, done) {
  const trimmed = (name || '').trim();
  done();
  if (!trimmed || !props.item?.wishlist_id) return;
  try {
    const { data } = await api.post(`/wishlists/${props.item.wishlist_id}/categories`, {
      name: trimmed,
    });
    emit('category-created', data);
    form.category_id = data.id;
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.response?.data?.detail || t('item.categoryCreateFailed'),
    });
  }
}

async function submit() {
  if (!form.title) return;
  saving.value = true;
  try {
    const { data } = await api.put(`/wishlists/items/${form.id}`, {
      title: form.title,
      description: form.description || null,
      url: form.url || null,
      image_url: form.image_url || null,
      price: form.price === '' ? null : form.price,
      currency: form.currency || null,
      category_id: form.category_id || null,
      priority: form.priority,
      quantity: form.quantity === '' ? null : form.quantity,
    });
    emit('saved', data);
    $q.notify({ type: 'positive', message: t('item.saved') });
    close();
  } catch (e) {
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || 'Error' });
  } finally {
    saving.value = false;
  }
}

function remove() {
  $q.dialog({
    title: t('item.deleteConfirmTitle'),
    message: t('item.deleteConfirmMessage', { title: form.title }),
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await api.delete(`/wishlists/items/${form.id}`);
      emit('deleted', { id: form.id });
      $q.notify({ type: 'positive', message: t('item.deleted') });
      close();
    } catch (e) {
      $q.notify({ type: 'negative', message: e?.response?.data?.detail || t('item.deleteFailed') });
    }
  });
}

async function archive() {
  try {
    await api.put(`/wishlists/items/${form.id}`, { archived: true });
    emit('archived', { id: form.id });
    $q.notify({ type: 'positive', message: t('item.archived') });
    close();
  } catch (e) {
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || t('item.archiveFailed') });
  }
}
</script>
