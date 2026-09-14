<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">{{ t('users.title') }}</div>
      <q-space />
      <q-btn
        color="primary"
        icon="person_add"
        :label="t('users.create')"
        @click="openCreate"
      />
    </div>

    <q-table
      :rows="users"
      :columns="columns"
      row-key="id"
      flat
      bordered
      :loading="loading"
    >
      <template #body-cell-role="props">
        <q-td :props="props">
          <q-chip :color="props.value === 'admin' ? 'deep-purple' : 'grey'" text-color="white" dense>
            {{ props.value }}
          </q-chip>
        </q-td>
      </template>

      <template #body-cell-is_active="props">
        <q-td :props="props">
          <q-toggle
            :model-value="props.value"
            checked-icon="check"
            color="positive"
            @update:model-value="(v) => setActive(props.row, v)"
          />
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn dense flat round icon="edit" @click="openEdit(props.row)">
            <q-tooltip>{{ t('common.edit') }}</q-tooltip>
          </q-btn>
          <q-btn
            dense
            flat
            round
            icon="delete"
            color="negative"
            :disable="props.row.id === auth.user?.id"
            @click="remove(props.row)"
          >
            <q-tooltip>{{ t('users.delete') }}</q-tooltip>
          </q-btn>
        </q-td>
      </template>
    </q-table>

    <!-- Create / edit dialog -->
    <q-dialog v-model="dialog.open">
      <q-card style="width: 480px; max-width: 92vw">
        <q-card-section class="text-h6">
          {{ dialog.row ? t('users.edit') : t('users.create') }}
        </q-card-section>
        <q-card-section>
          <q-input v-model="form.email" :label="t('users.email')" dense outlined class="q-mb-sm" :disable="!!dialog.row" />
          <q-input v-model="form.username" :label="t('users.username')" dense outlined class="q-mb-sm" />
          <q-input v-model="form.full_name" :label="t('users.fullName')" dense outlined class="q-mb-sm" />
          <q-input
            v-model="form.password"
            :label="dialog.row ? t('users.passwordReset') : t('users.password')"
            dense
            outlined
            type="password"
            class="q-mb-sm"
            :hint="dialog.row ? t('users.passwordHint') : ''"
          />
          <q-select
            v-model="form.role"
            :options="roleOptions"
            :label="t('users.role')"
            dense
            outlined
            emit-value
            map-options
            :disable="dialog.row && dialog.row.id === auth.user?.id"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" @click="dialog.open = false" />
          <q-btn color="primary" :label="t('common.save')" :loading="saving" @click="save" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';

const { t } = useI18n();
const $q = useQuasar();
const auth = useAuthStore();

const users = ref([]);
const loading = ref(false);
const saving = ref(false);
const dialog = ref({ open: false, row: null });
const form = ref({ email: '', username: '', full_name: '', password: '', role: 'user' });

const roleOptions = [
  { label: 'User', value: 'user' },
  { label: 'Admin', value: 'admin' },
];

const columns = [
  { name: 'email', label: t('users.email'), field: 'email', align: 'left' },
  { name: 'full_name', label: t('users.fullName'), field: 'full_name', align: 'left' },
  { name: 'role', label: t('users.role'), field: 'role', align: 'left' },
  { name: 'auth_provider', label: t('users.provider'), field: 'auth_provider', align: 'left' },
  { name: 'is_active', label: t('users.active'), field: 'is_active', align: 'center' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
];

async function load() {
  loading.value = true;
  try {
    const { data } = await api.get('/auth/users');
    users.value = data;
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  dialog.value = { open: true, row: null };
  form.value = { email: '', username: '', full_name: '', password: '', role: 'user' };
}

function openEdit(row) {
  dialog.value = { open: true, row };
  form.value = {
    email: row.email,
    username: row.username || '',
    full_name: row.full_name || '',
    password: '',
    role: row.role,
  };
}

async function save() {
  saving.value = true;
  try {
    if (dialog.value.row) {
      const payload = { role: form.value.role };
      if (form.value.password) payload.password = form.value.password;
      await api.put(`/auth/users/${dialog.value.row.id}`, payload);
    } else {
      await api.post('/auth/users', {
        email: form.value.email,
        username: form.value.username || null,
        full_name: form.value.full_name || null,
        password: form.value.password,
        role: form.value.role,
      });
    }
    dialog.value.open = false;
    $q.notify({ type: 'positive', message: t('users.saved') });
    await load();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
  } finally {
    saving.value = false;
  }
}

async function setActive(row, value) {
  try {
    await api.put(`/auth/users/${row.id}`, { is_active: value });
    row.is_active = value;
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
  }
}

async function remove(row) {
  $q.dialog({
    title: t('users.delete'),
    message: `${t('users.confirmDelete')} (${row.email})?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await api.delete(`/auth/users/${row.id}`);
      $q.notify({ type: 'positive', message: t('users.deleted') });
      await load();
    } catch (e) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
    }
  });
}

onMounted(load);
</script>
