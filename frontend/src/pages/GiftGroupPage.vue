<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        round
        dense
        icon="arrow_back"
        :aria-label="t('common.back')"
        @click="goBack"
      />
      <div class="text-h5" v-if="group">{{ group.name }}</div>
      <q-space />
      <q-btn
        v-if="isOwner && group"
        flat
        color="negative"
        :label="t('giftExchange.deleteGroup')"
        @click="removeGroup"
      />
    </div>

    <q-inner-loading :showing="loading" />

    <template v-if="group && isOwner">
      <div class="text-subtitle1 q-mt-md">{{ t('giftExchange.participants') }}</div>
      <q-list bordered separator>
        <q-item v-for="p in participants" :key="p.id">
          <q-item-section>
            <q-item-label>{{ p.name }}</q-item-label>
            <q-item-label caption v-if="p.family">
              {{ t('giftExchange.family') }}: {{ p.family }}
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
                @click="removeParticipant(p)"
              />
            </div>
          </q-item-section>
        </q-item>
      </q-list>

      <div class="q-mt-sm">
        <q-btn
          color="primary"
          icon="add"
          :label="t('giftExchange.addParticipant')"
          @click="openAdd"
        />
        <q-btn
          class="q-ml-sm"
          color="secondary"
          icon="casino"
          :label="t('giftExchange.runDraw')"
          :disable="participants.length < 2"
          @click="runDraw"
        />
      </div>

      <div class="text-subtitle1 q-mt-lg" v-if="assignments.length">
        {{ t('giftExchange.assignments') }}
      </div>
      <q-list bordered separator v-if="assignments.length">
        <q-item v-for="a in assignments" :key="a.giver_id">
          <q-item-section>
            <q-item-label>
              {{ t('giftExchange.givesTo', { giver: a.giver_name, receiver: a.receiver_name }) }}
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
      <q-banner
        v-else-if="!drawError"
        class="bg-grey-2 text-dark dark:bg-grey-9 dark:text-white rounded-borders q-mt-sm"
      >
        {{ t('giftExchange.noAssignments') }}
      </q-banner>
      <q-banner
        v-if="drawError"
        class="bg-amber-1 text-amber-10 rounded-borders q-mt-sm"
      >
        {{ drawError }}
      </q-banner>
    </template>

    <template v-else-if="group && !isOwner">
      <q-banner class="bg-blue-1 text-blue-10 q-mb-md rounded-borders dark:bg-blue-10 dark:text-blue-1">
        {{ t('giftExchange.participantView') }}
      </q-banner>
      <q-card flat bordered v-if="myAssignment">
        <q-card-section>
          {{ t('giftExchange.myAssignment', { name: myAssignment.receiver_name }) }}
        </q-card-section>
      </q-card>
      <q-banner v-else class="bg-grey-2 text-dark dark:bg-grey-9 dark:text-white rounded-borders">
        {{ t('giftExchange.noAssignments') }}
      </q-banner>
    </template>

    <q-dialog v-model="partOpen">
      <q-card style="min-width: 320px">
        <q-card-section>
          <div class="text-h6">{{ t('giftExchange.addParticipant') }}</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="partName"
            :label="t('giftExchange.name')"
            dense
            outlined
            autofocus
          />
          <q-input
            v-model="partFamily"
            :label="t('giftExchange.family')"
            dense
            outlined
            class="q-mt-sm"
            :hint="t('giftExchange.familyHint')"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" @click="partOpen = false" />
          <q-btn color="primary" :label="t('common.save')" @click="saveParticipant" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';
import { Dialog, Notify } from 'quasar';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const group = ref(null);
const loading = ref(false);
const participants = ref([]);
const assignments = ref([]);
const myAssignment = ref(null);
const drawError = ref('');

const isOwner = computed(
  () => group.value && group.value.owner_id === auth.user?.id,
);

const partOpen = ref(false);
const editingId = ref(null);
const partName = ref('');
const partFamily = ref('');

async function load() {
  loading.value = true;
  drawError.value = '';
  try {
    const { data } = await api.get(`/gift-exchange/groups/${route.params.id}`);
    group.value = data;
    if (isOwner.value) {
      participants.value = data.participants || [];
      const { data: a } = await api.get(
        `/gift-exchange/groups/${route.params.id}/assignments`,
      );
      assignments.value = a || [];
    } else {
      participants.value = [];
      myAssignment.value = data.my_assignment || null;
    }
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  editingId.value = null;
  partName.value = '';
  partFamily.value = '';
  partOpen.value = true;
}

function openEdit(p) {
  editingId.value = p.id;
  partName.value = p.name;
  partFamily.value = p.family || '';
  partOpen.value = true;
}

async function saveParticipant() {
  const name = partName.value.trim();
  if (!name) return;
  const body = { name, family: partFamily.value.trim() || null };
  if (editingId.value) {
    await api.put(
      `/gift-exchange/groups/${route.params.id}/participants/${editingId.value}`,
      body,
    );
  } else {
    await api.post(`/gift-exchange/groups/${route.params.id}/participants`, body);
  }
  partOpen.value = false;
  await load();
}

async function removeParticipant(p) {
  Dialog.create({
    title: t('giftExchange.removeParticipant'),
    message: p.name,
    cancel: true,
  }).onOk(async () => {
    await api.delete(
      `/gift-exchange/groups/${route.params.id}/participants/${p.id}`,
    );
    await load();
  });
}

async function runDraw() {
  Dialog.create({
    title: t('giftExchange.runDraw'),
    message: t('giftExchange.drawConfirm'),
    cancel: true,
  }).onOk(async () => {
    const { data } = await api.post(`/gift-exchange/groups/${route.params.id}/draw`);
    if (data.unsolvable) {
      drawError.value = data.message || t('giftExchange.unsolvable');
      assignments.value = [];
      return;
    }
    drawError.value = '';
    assignments.value = data.assignments || [];
    Notify.create({ type: 'positive', message: t('giftExchange.drawSuccess') });
    await load();
  });
}

async function removeGroup() {
  Dialog.create({
    title: t('giftExchange.deleteGroup'),
    cancel: true,
  }).onOk(async () => {
    await api.delete(`/gift-exchange/groups/${route.params.id}`);
    router.push('/gift-exchange');
  });
}

function goBack() {
  router.push('/gift-exchange');
}

onMounted(load);
</script>
