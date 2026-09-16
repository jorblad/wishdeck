<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">My Wishlists</div>
    <q-btn
      v-if="auth.isAuthenticated"
      color="primary"
      icon="add"
      :label="$t('menu.newWishlist')"
      data-testid="new-wishlist"
      @click="createWishlist"
    />

    <q-list bordered separator class="q-mt-md">
      <q-item v-for="wl in wishlists" :key="wl.id">
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
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';
import QuickAddDialog from 'components/QuickAddDialog.vue';
import WishlistEditDialog from 'components/WishlistEditDialog.vue';

const router = useRouter();
const $q = useQuasar();
const auth = useAuthStore();
const wishlists = ref([]);
const quickAdd = ref({ open: false, wishlistId: '', categories: [] });
const editDialog = ref({ open: false, wishlist: null });

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
