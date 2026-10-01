<template>
  <q-select
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :options="options"
    :label="label"
    use-input
    emit-value
    map-options
    clearable
    dense
    outlined
    :input-debounce="200"
    @filter="onFilter"
  />
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { api } from 'boot/axios';

const props = defineProps({
  modelValue: { type: String, default: null },
  label: { type: String, default: 'Link to user' },
});
const emit = defineEmits(['update:modelValue']);

const options = ref([]);

async function onFilter(val, update) {
  const { data } = await api.get('/users', { params: { q: val || '' } });
  update(() => {
    options.value = data.map((u) => ({
      label: u.full_name || u.email,
      value: u.id,
    }));
  });
}

onMounted(() => onFilter('', () => {}));
</script>
