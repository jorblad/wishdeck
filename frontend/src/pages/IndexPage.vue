<template>
  <q-page class="q-pa-md">

    <!-- Anonymous welcome: public lists are browsable without an account. -->
    <q-banner
      v-if="authReady && !auth.isAuthenticated"
      class="bg-primary text-white rounded-borders q-mb-lg"
    >
      <template #avatar><q-icon name="celebration" /></template>
      <div class="text-h6">{{ t('index.welcomeTitle') }}</div>
      <div class="q-mt-xs">{{ t('index.welcomeText') }}</div>
      <div class="q-mt-sm row q-gutter-sm">
        <q-btn color="white" text-color="primary" :label="t('auth.signIn')" @click="router.push('/login')" />
        <q-btn outline color="white" :label="t('auth.createAnAccount')" @click="router.push('/login')" />
      </div>
    </q-banner>

    <!-- My Wishlists (authenticated only) -->
    <template v-if="authReady && auth.isAuthenticated">
    <div class="text-h5 q-mb-md">{{ $t('index.myWishlists') }}</div>
      <q-btn
        v-if="auth.isAuthenticated"
        color="primary"
        icon="add"
        :label="$t('menu.newWishlist')"
        data-testid="new-wishlist"
        @click="createOpen = true"
      />

    <template v-if="publicSettings.featureGiftExchange">
      <div class="text-h6 q-mt-lg">{{ t('index.giftExchange') }}</div>
      <div class="row q-col-gutter-md q-mt-xs">
        <div
          v-for="g in giftGroups"
          :key="g.id"
          class="col-12 col-sm-6 col-md-4"
        >
          <q-card flat bordered class="cursor-pointer" @click="openGroup(g)">
            <q-card-section>
              <div class="row items-center no-wrap">
                <div class="text-subtitle1 text-weight-medium ellipsis">{{ g.name }}</div>
                <q-space />
                <q-chip
                  size="sm"
                  :color="g.owner_id === auth.user?.id ? 'primary' : 'teal'"
                  text-color="white"
                >
                  {{ g.owner_id === auth.user?.id ? t('index.owner') : t('index.participant') }}
                </q-chip>
              </div>
              <div v-if="g.my_assignment" class="q-mt-sm row items-center q-gutter-xs">
                <q-icon name="card_giftcard" color="primary" />
                <span class="text-body1">
                  {{ t('index.giveTo', { name: g.my_assignment.receiver_name }) }}
                </span>
              </div>
              <div v-else class="q-mt-sm text-caption text-grey-7">
                {{ t('index.noAssignment') }}
              </div>
              <div
                v-if="g.owner_id === auth.user?.id && g.my_assignment"
                class="text-caption text-grey-7 q-mt-xs"
              >
                {{ g.members.length }} · {{ t('giftExchange.participants') }}
              </div>
            </q-card-section>
          </q-card>
        </div>
        <div v-if="!giftLoading && !giftGroups.length" class="col-12">
          <q-banner class="bg-grey-2 text-dark dark:bg-grey-9 dark:text-white rounded-borders">
            {{ t('index.noGiftGroups') }}
          </q-banner>
        </div>
      </div>
    </template>

    <div class="row q-col-gutter-sm q-mt-md">
      <div class="col-12 col-sm-5">
        <q-select
          v-model="sortBy"
          :options="sortOptions"
          :label="t('index.sort.label')"
          dense
          outlined
          emit-value
          map-options
        />
      </div>
      <div class="col-12 col-sm-4">
        <q-select
          v-model="filterVisibility"
          :options="visibilityOptions"
          :label="t('index.filter.visibility')"
          dense
          outlined
          emit-value
          map-options
        />
      </div>
      <div class="col-12 col-sm-3">
        <q-toggle
          v-model="filterArchived"
          :label="t('index.filter.archived')"
          class="q-mt-sm"
        />
      </div>
    </div>

    <q-list bordered separator class="q-mt-md">
      <q-item
        v-for="wl in filteredWishlists"
        :key="wl.id"
        clickable
        v-ripple
        @click="open(wl)"
        :class="$q.screen.lt.sm ? 'column items-start' : 'row items-center'"
      >
        <div class="col">
          <div class="text-primary text-weight-medium">
            {{ wl.title }}
            <q-chip
              v-if="wl.shared_with_me"
              size="sm"
              color="teal"
              text-color="white"
              icon="group"
              class="q-ml-xs"
            >
              {{ wl.can_edit ? t('collaborators.shared') : t('collaborators.sharedView') }}
            </q-chip>
          </div>
          <q-chip
            dense
            size="sm"
            class="q-mt-xs q-px-sm"
            :color="visibilityColor(wl.visibility)"
            :text-color="visibilityTextColor(wl.visibility)"
            :icon="visibilityIcon(wl.visibility)"
          >
            {{ t('visibility.' + wl.visibility) }}
          </q-chip>
        </div>
        <div class="col-auto" :class="$q.screen.lt.sm ? 'self-stretch q-mt-sm' : 'q-ml-auto'">
          <div class="row q-gutter-xs items-center" :class="$q.screen.lt.sm ? 'justify-start' : 'justify-end'">
            <q-btn
              dense
              flat
              round
              icon="edit"
              :disable="!wl.can_edit"
              @click.stop="openEdit(wl)"
            >
              <q-tooltip>{{ $t('wishlist.editTitle') }}</q-tooltip>
            </q-btn>
            <q-btn
              dense
              flat
              round
              icon="add_shopping_cart"
              :disable="!wl.can_edit"
              @click.stop="openQuickAdd(wl)"
            >
              <q-tooltip>{{ $t('quickAdd.add') }}</q-tooltip>
            </q-btn>
            <template v-if="canManage(wl)">
              <q-btn
                dense
                flat
                round
                :icon="wl.archived ? 'unarchive' : 'archive'"
                :color="wl.archived ? 'warning' : ''"
                @click.stop="toggleArchive(wl)"
              >
                <q-tooltip>{{ wl.archived ? t('index.unarchiveList') : t('index.archiveList') }}</q-tooltip>
              </q-btn>
              <q-btn
                dense
                flat
                round
                icon="delete"
                color="negative"
                @click.stop="removeWishlist(wl)"
              >
                <q-tooltip>{{ t('index.deleteList') }}</q-tooltip>
              </q-btn>
            </template>
          </div>
        </div>
      </q-item>
    </q-list>
    </template>

    <!-- Public wishlists: visible to everyone (including logged-out visitors). -->
    <div class="text-h5 q-mt-lg">{{ t('index.publicWishlists') }}</div>
    <div class="text-subtitle2 text-grey-7 q-mb-sm">{{ t('index.browsePublic') }}</div>
    <div class="row q-col-gutter-md">
      <div
        v-for="p in publicWishlists"
        :key="p.id"
        class="col-12 col-sm-6 col-md-4"
      >
        <q-card flat bordered class="cursor-pointer" @click="router.push(`/wishlists/${p.slug}`)">
          <q-img
            v-if="p.cover_image"
            :src="p.cover_image"
            ratio="16/9"
            spinner-color="primary"
          >
            <div class="absolute-bottom text-subtitle2 text-weight-medium">
              {{ p.title }}
            </div>
          </q-img>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium ellipsis">{{ p.title }}</div>
            <div class="text-caption text-grey-7 q-mt-xs">
              {{ t('index.byOwner', { name: p.owner_name || t('index.unknownOwner') }) }}
            </div>
            <div class="text-caption text-grey-7">
              {{ t('index.itemsCount', { count: p.item_count }) }}
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div v-if="!publicLoading && !publicWishlists.length" class="col-12">
        <q-banner class="bg-grey-2 text-dark dark:bg-grey-9 dark:text-white rounded-borders">
          {{ t('index.noPublicWishlists') }}
        </q-banner>
      </div>
    </div>

    <QuickAddDialog
      v-model="quickAdd.open"
      :wishlist-id="quickAdd.wishlistId"
      :categories="quickAdd.categories"
      @added="onAdded"
      @category-created="onCategoryCreated"
    />

    <WishlistEditDialog
      v-model="editDialog.open"
      :wishlist="editDialog.wishlist"
      @saved="onSaved"
    />

    <WishlistEditDialog
      v-model="createOpen"
      :wishlist="null"
      @saved="onCreated"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';
import { usePublicSettingsStore } from 'stores/publicSettings';
import QuickAddDialog from 'components/QuickAddDialog.vue';
import WishlistEditDialog from 'components/WishlistEditDialog.vue';

const router = useRouter();
const { t } = useI18n();
const $q = useQuasar();
const auth = useAuthStore();
const publicSettings = usePublicSettingsStore();
const wishlists = ref([]);
const giftGroups = ref([]);
const giftLoading = ref(false);
const publicWishlists = ref([]);
const publicLoading = ref(false);
const authReady = ref(false);
const quickAdd = ref({ open: false, wishlistId: '', categories: [] });
const editDialog = ref({ open: false, wishlist: null });
const createOpen = ref(false);
const sortBy = ref('newest');
const filterVisibility = ref('all');
const filterArchived = ref(false);

const sortOptions = computed(() => [
  { label: t('index.sort.newest'), value: 'newest' },
  { label: t('index.sort.oldest'), value: 'oldest' },
  { label: t('index.sort.titleAsc'), value: 'titleAsc' },
  { label: t('index.sort.titleDesc'), value: 'titleDesc' },
]);

const visibilityOptions = computed(() => [
  { label: t('index.filter.all'), value: 'all' },
  { label: t('visibility.private'), value: 'private' },
  { label: t('visibility.unlisted'), value: 'unlisted' },
  { label: t('visibility.public'), value: 'public' },
]);

const filteredWishlists = computed(() => {
  let rows = wishlists.value.filter((wl) => {
    if (filterVisibility.value !== 'all' && wl.visibility !== filterVisibility.value) return false;
    if (!filterArchived.value && wl.archived) return false;
    return true;
  });
  rows = [...rows].sort((a, b) => {
    switch (sortBy.value) {
      case 'oldest':
        return new Date(a.created_at) - new Date(b.created_at);
      case 'titleAsc':
        return a.title.localeCompare(b.title);
      case 'titleDesc':
        return b.title.localeCompare(a.title);
      case 'newest':
      default:
        return new Date(b.created_at) - new Date(a.created_at);
    }
  });
  return rows;
});

async function load() {
  const { data } = await api.get('/wishlists');
  wishlists.value = data;
}
async function loadGiftGroups() {
  if (!publicSettings.featureGiftExchange) return;
  giftLoading.value = true;
  try {
    const { data } = await api.get('/gift-exchange/groups');
    giftGroups.value = data || [];
  } catch {
    giftGroups.value = [];
  } finally {
    giftLoading.value = false;
  }
}
async function loadPublic() {
  publicLoading.value = true;
  try {
    const { data } = await api.get('/wishlists/public');
    publicWishlists.value = data || [];
  } catch {
    publicWishlists.value = [];
  } finally {
    publicLoading.value = false;
  }
}
function openGroup(g) {
  router.push(`/gift-exchange/${g.id}`);
}
function onCreated(data) {
  router.push(`/wishlists/owner/${data.id}`);
}
function open(wl) {
  router.push(`/wishlists/owner/${wl.id}`);
}
async function openQuickAdd(wl) {
  const { data } = await api.get(`/wishlists/${wl.id}`);
  quickAdd.value = { open: true, wishlistId: wl.id, categories: data.categories || [] };
}
async function openEdit(wl) {
  editDialog.value = { open: true, wishlist: wl };
}
function onAdded() {
  // Item was created; take the user to the wishlist so they can see it.
  $q.notify({ type: 'positive', message: 'Item added' });
  router.push(`/wishlists/owner/${quickAdd.value.wishlistId}`);
}
function onSaved() {
  load();
}
function onCategoryCreated(cat) {
  if (!quickAdd.value.categories.find((c) => c.id === cat.id)) {
    quickAdd.value.categories.push(cat);
  }
}
function canManage(wl) {
  return !!wl.can_manage;
}
function visibilityColor(visibility) {
  if (visibility === 'public') return 'green';
  if (visibility === 'unlisted') return 'amber';
  return 'grey-8';
}
function visibilityTextColor(visibility) {
  // Amber is a light background; dark text keeps the label legible.
  // Green and grey-8 read better with white text.
  return visibility === 'unlisted' ? 'dark' : 'white';
}
function visibilityIcon(visibility) {
  if (visibility === 'public') return 'public';
  if (visibility === 'unlisted') return 'link';
  return 'lock';
}
async function toggleArchive(wl) {
  try {
    await api.put(`/wishlists/${wl.id}`, { archived: !wl.archived });
    wl.archived = !wl.archived;
    $q.notify({ type: 'positive', message: wl.archived ? t('index.listArchived') : t('index.listUnarchived') });
  } catch (e) {
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || 'Error' });
  }
}
function removeWishlist(wl) {
  $q.dialog({
    title: t('index.deleteList'),
    message: t('index.confirmDeleteList', { title: wl.title }),
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await api.delete(`/wishlists/${wl.id}`);
      wishlists.value = wishlists.value.filter((w) => w.id !== wl.id);
      $q.notify({ type: 'positive', message: t('index.listDeleted') });
    } catch (e) {
      $q.notify({ type: 'negative', message: e?.response?.data?.detail || 'Error' });
    }
  });
}
onMounted(async () => {
  if (!publicSettings.loaded) await publicSettings.load();
  // Determine auth state (also covers a full page reload at "/").
  await auth.fetchMe();
  authReady.value = true;
  // Public lists are browsable by everyone, including logged-out visitors.
  loadPublic();
  if (auth.isAuthenticated) {
    load();
    loadGiftGroups();
  }
});
</script>
