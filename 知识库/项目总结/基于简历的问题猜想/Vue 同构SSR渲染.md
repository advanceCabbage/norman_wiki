Vue 同构 SSR 的核心是：同一套 Vue 组件代码运行两次。

- 第一次在 Node 服务端运行，把业务组件渲染成真实 HTML；
- 第二次在浏览器运行，不重新创建整棵 DOM，而是接管服务端已有 DOM、绑定事件，使页面可交互。第二步叫 hydration（激活）。

Vue 同构 SSR 的原理是同一套 Vue 组件代码分别在服务端和浏览器运行：
- 用户首次请求页面时，Node 服务端根据 URL 创建独立的 Vue、Router 和 Store 实例，先获取首屏数据，再将 Vue 组件渲染成包含真实业务内容的 HTML 返回；同时把初始状态序列化到页面中。
- 浏览器下载客户端 Bundle 后，用相同的路由和初始状态重新创建 Vue 应用，对服务端已有 DOM 进行 Hydration，也就是复用 DOM 并绑定事件，使静态 HTML 变成可交互应用。
- 这样首屏无需等待 JS 下载执行就能看到内容，利于首屏性能和 SEO，但要保证服务端与客户端渲染结果一致，并避免在服务端直接使用 `window`、`document` 等浏览器 API

#### SSR 落地的一些坑
- `window`、`document`、`localStorage`、地图 SDK 等浏览器 API，不能在服务端直接访问；应放到 `mounted` 中。
- 每个请求必须新建 Router、Store、Vue App，防止跨用户状态污染。
- 服务端取数与客户端初始状态必须一致，否则 hydration mismatch。
- 需要两套构建：Server Bundle 与 Client Bundle。
- Node SSR 会消耗 CPU；用户态页面还要谨慎缓存，不能把一个用户的 HTML 缓存给另一用户