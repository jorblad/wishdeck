<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">{{ t('giftExchange.title') }}</div>
      <q-space />
      <q-btn
        color="primary"
        icon="add"
        :label="t('giftExchange.createGroup')"
        @click="createOpen = true"
      />
    </div>

    <div class="text-subtitle2 text-grey-7 q-mb-md">{{ t('giftExchange.subtitle') }}</div>

    <q-list bordered separator v-if="groups.length">
      <q-item
        v-for="g in groups"
        :key="g.id"
        clickable
        v-ripple
        @click="open(g.id)"
      >
        <q-item-section>
          <q-item-label>{{ g.name }}</q-item-label>
          <q-item-label caption v-if="!isOwner(g)">
            {{ t('giftExchange.participantView') }}
          </q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-item-label caption>
            {{ g.participants.length }} · {{ t('giftExchange.participants') }}
          </q-item-label>
        </q-item-section>
      </q-item>
    </q-list>

    <q-banner v-else-if="!loading" class="bg-grey-2 rounded-borders">
      {{ t('giftExchange.noGroups') }}
    </q-banner>

    <q-inner-loading :showing="loading" />

    <q-dialog v-model="createOpen">
      <q-card style="min-width: 320px">
        <q-card-section>
          <div class="text-h6">{{ t('giftExchange.createGroup') }}</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="newName"
            :label="t('giftExchange.groupName')"
            dense
            outlined
            autofocus
            @keyup.enter="create"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" @click="createOpen = false" />
          <q-btn color="primary" :label="t('common.save')" @click="create" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();

const groups = ref([]);
const loading = ref(false);
const createOpen = ref(false);
const newName = ref('');

function isOwner(g) {
  return g.owner_id === auth.user?.id;
}

async function load() {
  loading.value = true;
  try {
    const { data } = await api.get('/gift-exchange/groups');
    groups.value = data;
  } finally {
    loading.value = false;
  }
}

async function create() {
  const name = newName.value.trim();
  if (!name) return;
  await api.post('/gift-exchange/groups', { name });
  newName.value = '';
  createOpen.value = false;
  await load();
}

function open(id) {
  router.push(`/gift-exchange/${id}`);
}

onMounted(load);
</script>
