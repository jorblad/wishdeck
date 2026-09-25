<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 560px; max-width: 94vw">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ t('collaborators.title') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="close" />
      </q-card-section>

      <q-card-section>
        <!-- Current collaborators -->
        <div v-if="shares.length" class="q-mb-md">
          <div
            v-for="s in shares"
            :key="s.id"
            class="row items-center q-gutter-sm q-mb-xs"
          >
            <q-avatar size="32px" color="primary" text-color="white">
              {{ initial(s.user) }}
            </q-avatar>
            <div class="col">
              <div class="text-subtitle2">{{ s.user.full_name || s.user.email }}</div>
              <div class="text-caption text-grey">{{ s.user.email }}</div>
            </div>
            <q-toggle
              :model-value="s.can_edit"
              :label="s.can_edit ? t('collaborators.canEdit') : t('collaborators.viewOnly')"
              left-label
              @update:model-value="(v) => setEdit(s, v)"
            />
            <q-btn
              flat
              round
              dense
              icon="person_remove"
              color="negative"
              :disable="busy === s.id"
              @click="remove(s)"
            >
              <q-tooltip>{{ t('collaborators.remove') }}</q-tooltip>
            </q-btn>
          </div>
        </div>
        <div v-else class="text-caption text-grey q-mb-md">{{ t('collaborators.none') }}</div>

        <!-- Add collaborator -->
        <q-select
          v-model="selected"
          :options="userOptions"
          :label="t('collaborators.add')"
          dense
          outlined
          use-input
          fill-input
          hide-selected
          option-value="id"
          option-label="label"
          :input-debounce="200"
          @filter="searchUsers"
        >
          <template #no-option>
            <q-item><q-item-section class="text-grey">{{ t('collaborators.noUsers') }}</q-item-section></q-item>
          </template>
          <template #after>
            <q-toggle v-model="newCanEdit" :label="t('collaborators.canEdit')" />
          </template>
        </q-select>
        <q-btn
          class="q-mt-sm"
          color="primary"
          :label="t('collaborators.share')"
          :disable="!selected"
          :loading="adding"
          @click="add"
        />
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  wishlistId: { type: String, required: true },
});
const emit = defineEmits(['update:modelValue', 'changed']);

const { t } = useI18n();
const $q = useQuasar();

const shares = ref([]);
const userOptions = ref([]);
const selected = ref(null);
const newCanEdit = ref(true);
const adding = ref(false);
const busy = ref(null);

function initial(u) {
  const name = u.full_name || u.email || '?';
  return name.charAt(0).toUpperCase();
}

function labelFor(u) {
  return u.full_name ? `${u.full_name} (${u.email})` : u.email;
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      selected.value = null;
      userOptions.value = [];
      loadShares();
    }
  }
);

async function loadShares() {
  try {
    const { data } = await api.get(`/wishlists/${props.wishlistId}/shares`);
    shares.value = data;
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
  }
}

async function searchUsers(val, update) {
  if (!val) {
    update(() => (userOptions.value = []));
    return;
  }
  try {
    const { data } = await api.get('/users', { params: { q: val } });
    update(() => {
      userOptions.value = data
        .filter((u) => !shares.value.find((s) => s.user_id === u.id))
        .map((u) => ({ ...u, label: labelFor(u) }));
    });
  } catch {
    update(() => (userOptions.value = []));
  }
}

async function add() {
  if (!selected.value || !selected.value.id) return;
  adding.value = true;
  try {
    await api.post(`/wishlists/${props.wishlistId}/shares`, {
      user_id: selected.value.id,
      can_edit: newCanEdit.value,
    });
    selected.value = null;
    await loadShares();
    emit('changed');
    $q.notify({ type: 'positive', message: t('collaborators.added') });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
  } finally {
    adding.value = false;
  }
}

async function setEdit(share, value) {
  busy.value = share.id;
  try {
    await api.put(`/wishlists/${props.wishlistId}/shares/${share.user_id}`, {
      can_edit: value,
    });
    share.can_edit = value;
    emit('changed');
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
  } finally {
    busy.value = null;
  }
}

async function remove(share) {
  busy.value = share.id;
  try {
    await api.delete(`/wishlists/${props.wishlistId}/shares/${share.user_id}`);
    shares.value = shares.value.filter((s) => s.id !== share.id);
    emit('changed');
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
  } finally {
    busy.value = null;
  }
}

function close() {
  emit('update:modelValue', false);
}
</script>
