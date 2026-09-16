<template>
  <q-layout view="hHh lpR fFf">
    <q-page-container>
      <q-page class="q-pa-md flex flex-center">
        <div class="text-center">
          <q-icon name="error" size="64px" color="grey-7" />
          <div class="text-h6 q-mt-sm">{{ $t('error.notFound') }}</div>
          <q-btn flat color="primary" :label="$t('error.goHome')" to="/" class="q-mt-md" />
        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>
