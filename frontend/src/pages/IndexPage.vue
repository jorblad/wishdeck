<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">{{ $t('index.myWishlists') }}</div>
    <q-btn
      v-if="auth.isAuthenticated"
      color="primary"
      icon="add"
      :label="$t('menu.newWishlist')"
      data-testid="new-wishlist"
      @click="createWishlist"
    />

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
      <q-item v-for="wl in filteredWishlists" :key="wl.id">
        <q-item-section clickable @click="open(wl)">
          <q-item-label>{{ wl.title }}</q-item-label>
          <q-item-label caption>{{ wl.visibility }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-btn
            dense
            flat
            round
            icon="edit"
            @click.stop="openEdit(wl)"
          >
            <q-tooltip>{{ $t('wishlist.editTitle') }}</q-tooltip>
          </q-btn>
          <q-btn
            dense
            flat
            round
            icon="add_shopping_cart"
            @click.stop="openQuickAdd(wl)"
          >
            <q-tooltip>{{ $t('quickAdd.add') }}</q-tooltip>
          </q-btn>
        </q-item-section>
      </q-item>
    </q-list>

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
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';
import QuickAddDialog from 'components/QuickAddDialog.vue';
import WishlistEditDialog from 'components/WishlistEditDialog.vue';

const router = useRouter();
const { t } = useI18n();
const $q = useQuasar();
const auth = useAuthStore();
const wishlists = ref([]);
const quickAdd = ref({ open: false, wishlistId: '', categories: [] });
const editDialog = ref({ open: false, wishlist: null });
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
async function createWishlist() {
  const { data } = await api.post('/wishlists', { title: 'New Wishlist' });
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
onMounted(load);
</script>
