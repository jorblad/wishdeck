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
        <q-item v-for="p in members" :key="p.id">
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
              <q-btn dense flat round icon="edit" @click="openEditPerson(p)" />
              <q-btn
                dense
                flat
                round
                icon="delete"
                color="negative"
                @click="removeMember(p)"
              />
            </div>
          </q-item-section>
        </q-item>
      </q-list>

      <div class="q-mt-sm">
        <q-btn
          color="primary"
          icon="add"
          :label="t('giftExchange.addMember')"
          @click="openAdd"
        />
        <q-btn
          class="q-ml-sm"
          color="secondary"
          icon="casino"
          :label="t('giftExchange.runDraw')"
          :disable="members.length < 2"
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
        class="bg-amber-1 text-amber-10 q-mb-md rounded-borders dark:bg-amber-10 dark:text-blue-1"
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
      <q-banner
        v-else
        class="bg-grey-2 text-dark dark:bg-grey-9 dark:text-white rounded-borders"
      >
        {{ t('giftExchange.noAssignments') }}
      </q-banner>
    </template>

    <!-- Add member dialog -->
    <q-dialog v-model="addOpen">
      <q-card style="min-width: 320px">
        <q-card-section>
          <div class="text-h6">{{ t('giftExchange.addMember') }}</div>
        </q-card-section>
        <q-card-section>
          <q-select
            v-model="selectedPersonId"
            :options="peopleOptions"
            :label="t('giftExchange.person')"
            dense
            outlined
            use-input
            emit-value
            map-options
            clearable
            :input-debounce="200"
            @filter="filterPeople"
            class="q-mb-sm"
          />
          <q-input
            v-model="newPersonName"
            :label="t('giftExchange.newPerson')"
            dense
            outlined
            class="q-mb-sm"
          />
          <FamilySelect
            v-model="personFamily"
            :label="t('giftExchange.family')"
            :hint="t('giftExchange.familyHint')"
            class="q-mb-sm"
          />
          <UserLinkSelect v-model="linkUserId" :label="t('giftExchange.linkUser')" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" @click="addOpen = false" />
          <q-btn color="primary" :label="t('common.save')" @click="saveMember" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Edit person dialog -->
    <q-dialog v-model="editOpen">
      <q-card style="min-width: 320px">
        <q-card-section>
          <div class="text-h6">{{ t('giftExchange.editPerson') }}</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="personForm.name"
            :label="t('giftExchange.name')"
            dense
            outlined
            class="q-mb-sm"
          />
          <FamilySelect
            v-model="personForm.family"
            :label="t('giftExchange.family')"
            :hint="t('giftExchange.familyHint')"
            class="q-mb-sm"
          />
          <UserLinkSelect
            v-model="personForm.user_id"
            :label="t('giftExchange.linkUser')"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" @click="editOpen = false" />
          <q-btn color="primary" :label="t('common.save')" @click="savePerson" />
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
import { Dialog } from 'quasar';
import FamilySelect from 'components/FamilySelect.vue';
import UserLinkSelect from 'components/UserLinkSelect.vue';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const group = ref(null);
const loading = ref(false);
const members = ref([]);
const assignments = ref([]);
const myAssignment = ref(null);
const drawError = ref('');

const isOwner = computed(
  () => group.value && group.value.owner_id === auth.user?.id,
);

const addOpen = ref(false);
const editOpen = ref(false);
const selectedPersonId = ref(null);
const newPersonName = ref('');
const personFamily = ref('');
const linkUserId = ref(null);
const peopleOptions = ref([]);
const editingPersonId = ref(null);
const personForm = ref({ name: '', family: '', user_id: null });

async function load() {
  loading.value = true;
  drawError.value = '';
  try {
    const { data } = await api.get(`/gift-exchange/groups/${route.params.id}`);
    group.value = data;
    if (isOwner.value) {
      members.value = data.members || [];
      const { data: a } = await api.get(
        `/gift-exchange/groups/${route.params.id}/assignments`,
      );
      assignments.value = a || [];
    } else {
      members.value = [];
      myAssignment.value = data.my_assignment || null;
    }
  } finally {
    loading.value = false;
  }
}

async function filterPeople(val, update) {
  const { data } = await api.get('/people', { params: { q: val || '' } });
  update(() => {
    peopleOptions.value = data.map((p) => ({
      label: p.name + (p.family ? ` (${p.family})` : ''),
      value: p.id,
    }));
  });
}

function openAdd() {
  selectedPersonId.value = null;
  newPersonName.value = '';
  personFamily.value = '';
  linkUserId.value = null;
  peopleOptions.value = [];
  addOpen.value = true;
}

async function saveMember() {
  if (selectedPersonId.value) {
    await api.post(`/gift-exchange/groups/${route.params.id}/members`, {
      person_id: selectedPersonId.value,
    });
  } else if (newPersonName.value.trim()) {
    await api.post(`/gift-exchange/groups/${route.params.id}/members`, {
      name: newPersonName.value.trim(),
      family: personFamily.value.trim() || null,
      user_id: linkUserId.value || null,
    });
  } else {
    return;
  }
  addOpen.value = false;
  await load();
}

function openEditPerson(p) {
  editingPersonId.value = p.id;
  personForm.value = {
    name: p.name,
    family: p.family || '',
    user_id: p.user_id || null,
  };
  editOpen.value = true;
}

async function savePerson() {
  await api.put(`/people/${editingPersonId.value}`, {
    name: personForm.value.name,
    family: personForm.value.family || null,
    user_id: personForm.value.user_id || null,
  });
  editOpen.value = false;
  await load();
}

async function removeMember(p) {
  Dialog.create({
    title: t('giftExchange.removeParticipant'),
    message: p.name,
    cancel: true,
  }).onOk(async () => {
    await api.delete(
      `/gift-exchange/groups/${route.params.id}/members/${p.id}`,
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
