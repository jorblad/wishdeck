<template>
  <q-page class="q-pa-md">
    <div v-if="loading" class="text-center q-pa-xl"><q-spinner size="40px" /></div>
    <template v-else-if="wishlist">
      <div class="row items-start q-mb-xs">
        <div class="text-h5">{{ wishlist.title }}</div>
        <q-space />
        <q-btn
          flat
          round
          dense
          icon="share"
          :disable="wishlist.visibility === 'private'"
          @click="openShare"
        >
          <q-tooltip>{{ t('wishlist.share') }}</q-tooltip>
        </q-btn>
        <q-btn
          v-if="isOwner"
          flat
          round
          dense
          icon="add"
          @click="quickAddOpen = true"
        >
          <q-tooltip>{{ t('quickAdd.add') }}</q-tooltip>
        </q-btn>
        <q-btn
          flat
          round
          dense
          icon="edit"
          @click="openEdit"
        >
          <q-tooltip>{{ t('wishlist.editTitle') }}</q-tooltip>
        </q-btn>
      </div>
      <div v-if="wishlist.visibility === 'private'" class="text-caption text-negative q-mb-md">
        {{ t('wishlist.privateShareHint') }}
      </div>
      <div class="text-caption q-mb-md">{{ wishlist.description }}</div>

      <q-expansion-item
        v-for="cat in grouped"
        :key="cat.name"
        :label="cat.name"
        icon="label"
        default-opened
      >
        <q-list separator>
          <q-item
            v-for="item in cat.items"
            :key="item.id"
            clickable
            @click="openItem(item)"
          >
            <q-item-section avatar v-if="item.image_url">
              <q-avatar size="48px"><img :src="item.image_url" /></q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ item.title }}</q-item-label>
              <q-item-label caption>
                {{ item.price != null ? item.price + ' ' + (item.currency || '') : '' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side v-if="wishlist.allow_claims">
              <q-btn
                size="sm"
                :color="item.status === 'open' ? 'primary' : 'grey'"
                :label="item.status === 'open' ? t('wishlist.claim') : t('wishlist.status.' + item.status)"
                :disable="item.status !== 'open' || isOwner"
                @click.stop="claim(item)"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </q-expansion-item>
    </template>
    <div v-else class="text-center text-grey">{{ t('wishlist.notFound') }}</div>

    <WishlistEditDialog
      v-model="editDialog.open"
      :wishlist="editDialog.wishlist"
      @saved="onSaved"
    />

    <QuickAddDialog
      v-model="quickAddOpen"
      :wishlist-id="wishlist ? wishlist.id : ''"
      :categories="wishlist ? wishlist.categories : []"
      @added="onItemAdded"
      @category-created="onCategoryCreated"
    />

    <ItemInfoDialog
      v-model="itemDialog.open"
      :item="itemDialog.item"
      :is-owner="isOwner"
      :categories="wishlist ? wishlist.categories : []"
      @saved="onItemSaved"
    />

    <q-dialog v-model="shareOpen">
      <q-card style="width: 520px; max-width: 92vw">
        <q-card-section class="text-h6">{{ t('wishlist.share') }}</q-card-section>
        <q-card-section>
          <q-input
            :model-value="shareUrl"
            readonly
            outlined
            dense
            class="q-mb-sm"
          >
            <template #append>
              <q-btn flat round dense icon="content_copy" @click="copyLink" />
            </template>
          </q-input>
          <div class="text-caption text-grey">
            {{ t('wishlist.shareHint') }}
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.close')" @click="shareOpen = false" />
          <q-btn
            v-if="isOwner && wishlist.visibility === 'private'"
            color="primary"
            :label="t('wishlist.changeVisibility')"
            @click="openShareThenEdit"
          />
          <q-btn color="primary" :label="t('wishlist.copyLink')" @click="copyLink" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { copyToClipboard } from 'quasar';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';
import WishlistEditDialog from 'components/WishlistEditDialog.vue';
import QuickAddDialog from 'components/QuickAddDialog.vue';
import ItemInfoDialog from 'components/ItemInfoDialog.vue';

const route = useRoute();
const { t } = useI18n();
const $q = useQuasar();
const auth = useAuthStore();
const wishlist = ref(null);
const loading = ref(true);
const editDialog = ref({ open: false, wishlist: null });
const quickAddOpen = ref(false);
const itemDialog = ref({ open: false, item: null });
const shareOpen = ref(false);

const isOwner = computed(
  () => !!wishlist.value && wishlist.value.owner_id === auth.user?.id
);

const shareUrl = computed(() => {
  if (!wishlist.value?.slug) return '';
  return `${window.location.origin}/wishlists/${wishlist.value.slug}`;
});

function openShare() {
  shareOpen.value = true;
}
async function copyLink() {
  try {
    await copyToClipboard(shareUrl.value);
    $q.notify({ type: 'positive', message: t('wishlist.linkCopied') });
  } catch {
    $q.notify({ type: 'negative', message: t('wishlist.copyFailed') });
  }
}
function openShareThenEdit() {
  shareOpen.value = false;
  openEdit();
}

function openEdit() {
  editDialog.value = { open: true, wishlist: wishlist.value };
}
function onSaved() {
  load();
}
function onItemAdded() {
  load();
}
function onCategoryCreated(cat) {
  if (wishlist.value && !wishlist.value.categories.find((c) => c.id === cat.id)) {
    wishlist.value.categories.push(cat);
  }
}
function openItem(item) {
  const cat = wishlist.value?.categories?.find((c) => c.id === item.category_id);
  itemDialog.value = {
    open: true,
    item: { ...item, categoryName: cat ? cat.name : undefined },
  };
}
function onItemSaved() {
  load();
}

const grouped = computed(() => {
  if (!wishlist.value) return [];
  const map = {};
  for (const item of wishlist.value.items || []) {
    const name = item.category_id || t('wishlist.uncategorized');
    (map[name] ||= { name, items: [] }).items.push(item);
  }
  return Object.values(map);
});

async function claim(item) {
  await api.post(`/wishlists/items/${item.id}/claim`);
  await load();
}

async function load(attempt = 1) {
  loading.value = true;
  try {
    const data =
      route.name === 'owner-wishlist'
        ? (await api.get(`/wishlists/${route.params.id}`)).data
        : (await api.get(`/wishlists/public/${route.params.slug}`)).data;
    wishlist.value = data;
  } catch (e) {
    console.error('Wishlist load failed:', e);
    // Retry once after a short delay to handle transient races (e.g. service
    // worker or DB replication lag right after creation).
    if (attempt === 1) {
      setTimeout(() => load(attempt + 1), 300);
      return;
    }
    wishlist.value = null;
  } finally {
    loading.value = false;
  }
}
onMounted(() => load());
</script>
