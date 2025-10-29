// led-control WS2812B LED Controller Server
// Copyright 2022 jackw01. Released under the MIT License (see LICENSE for details).

import store from './Store.js';

import SetupPage from './pages/SetupPage.js';
import ControlPage from './pages/ControlPage.js';
import VisualizerPage from './pages/VisualizerPage.js';

import SliderNumberInput from './components/SliderNumberInput.js';
import PaletteColorBar from './components/PaletteColorBar.js';
import GroupControls from './components/GroupControls.js';
import GroupConfig from './components/GroupConfig.js';
import ArtnetConfig from './components/ArtnetConfig.js';

await store.load();

const routes = [
  { path: '/', component: ControlPage },
  { path: '/setup', component: SetupPage },
  { path: '/visualizer', component: VisualizerPage },
];

const router = VueRouter.createRouter({
  history: VueRouter.createWebHashHistory(),
  routes,
});

const app = Vue.createApp({});
app.component('slider-number-input', SliderNumberInput);
app.component('palette-color-bar', PaletteColorBar);
app.component('group-controls', GroupControls);
app.component('group-config', GroupConfig);
app.component('artnet-config', ArtnetConfig);
app.use(router);
app.mount('#main');
