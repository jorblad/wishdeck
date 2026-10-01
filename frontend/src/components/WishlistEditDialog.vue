<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 480px; max-width: 92vw">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ isCreate ? t('wishlist.newTitle') : t('wishlist.editTitle') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="close" />
      </q-card-section>

      <q-card-section>
        <q-input
          v-model="form.title"
          :label="t('wishlist.title')"
          dense
          outlined
          class="q-mb-sm"
          :rules="[(v) => !!v || t('common.required')]"
        />
        <q-input
          v-model="form.description"
          :label="t('wishlist.description')"
          dense
          outlined
          type="textarea"
          autogrow
          class="q-mb-sm"
        />
        <q-select
          v-model="form.visibility"
          :options="visibilityOptions"
          :label="t('wishlist.visibility')"
          dense
          outlined
          emit-value
          map-options
        />
        <q-toggle
          v-model="form.allow_claims"
          :label="t('wishlist.allowClaims')"
          class="q-mt-sm"
        />
        <q-select
          v-if="people.length"
          v-model="form.person_id"
          :options="personOptions"
          :label="t('wishlist.linkPerson')"
          dense
          outlined
          emit-value
          map-options
          clearable
          class="q-mt-sm"
        />
        <div v-if="people.length" class="text-caption text-grey-7 q-mt-xs">
          {{ t('wishlist.linkPersonHint') }}
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('common.cancel')" @click="close" />
        <q-btn
          color="primary"
          :label="t('common.save')"
          :loading="saving"
          :disable="!form.title"
          @click="submit"
        />
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
  wishlist: { type: Object, default: null },
});
const emit = defineEmits(['update:modelValue', 'saved']);

const { t } = useI18n();
const $q = useQuasar();

const saving = ref(false);
const form = reactive({
  id: null,
  title: '',
  description: '',
  visibility: 'private',
  allow_claims: true,
  person_id: null,
});
const people = ref([]);

const isCreate = computed(() => !props.wishlist);

const visibilityOptions = computed(() => [
  { label: t('visibility.private'), value: 'private' },
  { label: t('visibility.unlisted'), value: 'unlisted' },
  { label: t('visibility.public'), value: 'public' },
]);

const personOptions = computed(() => [
  { label: t('wishlist.personNone'), value: null },
  ...people.value.map((p) => ({ label: p.name, value: p.id })),
]);

async function loadPeople() {
  if (people.value.length) return;
  try {
    const { data } = await api.get('/people');
    people.value = Array.isArray(data) ? data : [];
  } catch {
    people.value = [];
  }
}

function resetForm() {
  form.id = null;
  form.title = '';
  form.description = '';
  form.visibility = 'private';
  form.allow_claims = true;
  form.person_id = null;
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    if (props.wishlist) {
      form.id = props.wishlist.id;
      form.title = props.wishlist.title || '';
      form.description = props.wishlist.description || '';
      form.visibility = props.wishlist.visibility || 'private';
      form.allow_claims = props.wishlist.allow_claims !== false;
      form.person_id = props.wishlist.person_id || null;
    } else {
      resetForm();
    }
    loadPeople();
  }
);

function close() {
  emit('update:modelValue', false);
}

async function submit() {
  if (!form.title) return;
  saving.value = true;
  try {
    const payload = {
      title: form.title,
      description: form.description || null,
      visibility: form.visibility,
      allow_claims: form.allow_claims,
      person_id: form.person_id || null,
    };
    let data;
    if (props.wishlist && props.wishlist.id) {
      const r = await api.put(`/wishlists/${form.id}`, payload);
      data = r.data;
      $q.notify({ type: 'positive', message: t('wishlist.saved') });
    } else {
      const r = await api.post('/wishlists', payload);
      data = r.data;
      $q.notify({ type: 'positive', message: t('wishlist.created') });
    }
    emit('saved', data);
    close();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Error',
    });
  } finally {
    saving.value = false;
  }
}
</script>
