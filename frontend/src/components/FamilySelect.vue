<template>
  <q-select
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :options="filtered"
    :label="label"
    :hint="hint"
    use-input
    new-value-mode="add"
    clearable
    dense
    outlined
    @filter="onFilter"
    @focus="load"
  />
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { api } from 'boot/axios';

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Family' },
  hint: { type: String, default: '' },
});
const emit = defineEmits(['update:modelValue']);

const all = ref([]);
const filtered = ref([]);

async function load() {
  try {
    const { data } = await api.get('/people/families');
    all.value = data || [];
  } catch {
    all.value = [];
  }
  if (!filtered.value.length) filtered.value = [...all.value];
}

function onFilter(val, update) {
  update(() => {
    const v = (val || '').toLowerCase();
    filtered.value = v
      ? all.value.filter((f) => f.toLowerCase().includes(v))
      : [...all.value];
  });
}

onMounted(load);
</script>
