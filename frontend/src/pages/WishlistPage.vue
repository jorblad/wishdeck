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
        <q-btn
          v-if="isOwner"
          flat
          round
          dense
          :icon="showArchived ? 'unarchive' : 'archive'"
          :color="showArchived ? 'warning' : ''"
          @click="showArchived = !showArchived"
        >
          <q-tooltip>{{ showArchived ? t('item.hideArchived') : t('item.showArchived') }}</q-tooltip>
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
            <q-item-section side>
              <template v-if="isOwner">
                <q-btn
                  v-if="!item.archived"
                  size="sm"
                  flat
                  round
                  icon="archive"
                  @click.stop="archiveItem(item)"
                >
                  <q-tooltip>{{ t('item.archive') }}</q-tooltip>
                </q-btn>
                <q-btn
                  v-else
                  size="sm"
                  flat
                  round
                  icon="unarchive"
                  color="warning"
                  @click.stop="unarchiveItem(item)"
                >
                  <q-tooltip>{{ t('item.unarchive') }}</q-tooltip>
                </q-btn>
                <q-btn
                  size="sm"
                  flat
                  round
                  icon="delete"
                  color="negative"
                  @click.stop="deleteItem(item)"
                >
                  <q-tooltip>{{ t('item.delete') }}</q-tooltip>
                </q-btn>
              </template>
              <q-btn
                v-else-if="wishlist.allow_claims"
                size="sm"
                :color="item.status === 'open' ? 'primary' : 'grey'"
                :label="item.status === 'open' ? t('wishlist.claim') : t('wishlist.status.' + item.status)"
                :disable="item.status !== 'open'"
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
      @deleted="onItemDeleted"
      @archived="onItemArchived"
      @category-created="onCategoryCreated"
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
import { computed, onMounted, ref, watch } from 'vue';
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
const showArchived = ref(false);

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
function onItemDeleted(item) {
  if (wishlist.value?.items) {
    wishlist.value.items = wishlist.value.items.filter((i) => i.id !== item.id);
  }
  $q.notify({ type: 'positive', message: t('item.deleted') });
}
function onItemArchived(item) {
  const local = wishlist.value?.items?.find((i) => i.id === item.id);
  if (local) local.archived = true;
  $q.notify({ type: 'positive', message: t('item.archived') });
}

const grouped = computed(() => {
  if (!wishlist.value) return [];
  const map = {};
  for (const item of wishlist.value.items || []) {
    if (item.archived && !showArchived.value) continue;
    const cat = wishlist.value.categories.find((c) => c.id === item.category_id);
    const name = cat ? cat.name : t('wishlist.uncategorized');
    (map[name] ||= { name, items: [] }).items.push(item);
  }
  return Object.values(map);
});

async function claim(item) {
  await api.post(`/wishlists/items/${item.id}/claim`);
  await load();
}
async function deleteItem(item) {
  $q.dialog({
    title: t('item.deleteConfirmTitle'),
    message: t('item.deleteConfirmMessage', { title: item.title }),
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await api.delete(`/wishlists/items/${item.id}`);
      onItemDeleted(item);
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e?.response?.data?.detail || t('item.deleteFailed'),
      });
    }
  });
}
async function archiveItem(item) {
  try {
    await api.put(`/wishlists/items/${item.id}`, { archived: true });
    onItemArchived(item);
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.response?.data?.detail || t('item.archiveFailed'),
    });
  }
}
async function unarchiveItem(item) {
  try {
    await api.put(`/wishlists/items/${item.id}`, { archived: false });
    item.archived = false;
    $q.notify({ type: 'positive', message: t('item.unarchived') });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.response?.data?.detail || t('item.unarchiveFailed'),
    });
  }
}

async function load(attempt = 1) {
  loading.value = true;
  try {
    const params = showArchived.value ? { include_archived: true } : {};
    const data =
      route.name === 'owner-wishlist'
        ? (await api.get(`/wishlists/${route.params.id}`, { params })).data
        : (await api.get(`/wishlists/public/${route.params.slug}`, { params })).data;
    wishlist.value = data;
  } catch (e) {
    console.error('Wishlist load failed:', e);
    $q.notify({
      type: 'negative',
      message: e?.response?.data?.detail || t('wishlist.loadFailed'),
    });
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
