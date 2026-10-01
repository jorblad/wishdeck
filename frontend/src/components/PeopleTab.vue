<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1">{{ t('giftExchange.peopleDirectory') }}</div>
      <q-space />
      <q-btn
        color="primary"
        icon="add"
        :label="t('giftExchange.addPerson')"
        @click="openAdd"
      />
    </div>

    <q-list bordered separator v-if="people.length">
      <q-item v-for="p in people" :key="p.id">
        <q-item-section>
          <q-item-label>{{ p.name }}</q-item-label>
          <q-item-label caption v-if="p.family">
            {{ t('giftExchange.family') }}: {{ p.family }}
          </q-item-label>
          <q-item-label caption v-if="p.user_id">
            <q-badge color="green" :label="t('giftExchange.linked')" />
          </q-item-label>
        </q-item-section>
        <q-item-section side>
          <div class="row q-gutter-xs">
            <q-btn dense flat round icon="edit" @click="openEdit(p)" />
            <q-btn
              dense
              flat
              round
              icon="delete"
              color="negative"
              @click="remove(p)"
            />
          </div>
        </q-item-section>
      </q-item>
    </q-list>

    <q-banner
      v-else
      class="bg-grey-2 text-dark dark:bg-grey-9 dark:text-white rounded-borders"
    >
      {{ t('giftExchange.noPeople') }}
    </q-banner>

    <q-dialog v-model="open">
      <q-card style="min-width: 320px">
        <q-card-section>
          <div class="text-h6">
            {{ editing ? t('giftExchange.editPerson') : t('giftExchange.addPerson') }}
          </div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="form.name"
            :label="t('giftExchange.name')"
            dense
            outlined
            autofocus
            class="q-mb-sm"
          />
          <FamilySelect
            v-model="form.family"
            :label="t('giftExchange.family')"
            :hint="t('giftExchange.familyHint')"
            class="q-mb-sm"
          />
          <UserLinkSelect v-model="form.user_id" :label="t('giftExchange.linkUser')" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" @click="open = false" />
          <q-btn color="primary" :label="t('common.save')" @click="save" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from 'boot/axios';
import { Dialog } from 'quasar';
import FamilySelect from 'components/FamilySelect.vue';
import UserLinkSelect from 'components/UserLinkSelect.vue';

const { t } = useI18n();

const people = ref([]);
const open = ref(false);
const editing = ref(false);
const editingId = ref(null);
const form = ref({ name: '', family: '', user_id: null });

async function load() {
  const { data } = await api.get('/people');
  people.value = data || [];
}

function openAdd() {
  editing.value = false;
  editingId.value = null;
  form.value = { name: '', family: '', user_id: null };
  open.value = true;
}

function openEdit(p) {
  editing.value = true;
  editingId.value = p.id;
  form.value = {
    name: p.name,
    family: p.family || '',
    user_id: p.user_id || null,
  };
  open.value = true;
}

async function save() {
  const payload = {
    name: form.value.name.trim(),
    family: form.value.family?.trim() || null,
    user_id: form.value.user_id || null,
  };
  if (!payload.name) return;
  if (editing.value) {
    await api.put(`/people/${editingId.value}`, payload);
  } else {
    await api.post('/people', payload);
  }
  open.value = false;
  await load();
}

function remove(p) {
  Dialog.create({
    title: t('giftExchange.deletePerson'),
    message: p.name,
    cancel: true,
  }).onOk(async () => {
    await api.delete(`/people/${p.id}`);
    await load();
  });
}

onMounted(load);
</script>
