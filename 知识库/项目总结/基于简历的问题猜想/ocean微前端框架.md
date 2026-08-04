## 一、三个仓库作用
- `platform-microservice`：微前端的服务端编排层。Egg 接收所有页面请求，识别 URL 属于哪个子应用，查到该应用的配置与资源清单，使用 `.hbs` 模板生成 HTML
- `ocean-layout`：主应用的统一壳，技术栈是react。负责 Header、侧边栏、Tab、面包屑等跨系统 UI
- `new-house-admin`：一个 Vue 2 子应用，只负责业务内容区域，挂载到页面中的 `#root`

## 二、主应用如何加载不同子应用

#### 2.1 服务端拼装 HTML 文件
Egg 的兜底路由接管页面请求，例如 `/new-house-admin/...`。它从 URL 的第一个路径段取出模块名 `new-house-admin`，再从缓存/数据库中的应用配置找到：
- `manifestPath`：该子应用的 `mapping.json` 地址
- `appBaseUrl`：静态资源根地址
服务端请求 mapping.json 文件，获得子应用的 JS 和 CSS 文件地址，**然后**将 CSS 地址拼接在 HTML 的 head 标签中，JS 地址拼接在 body 标签中并设置 preload。帮助浏览器再解析时 html 时更快加载子应用的 JS 和 CSS 文件

#### 2.2 具体服务端渲染流程
这是服务端 HTML 组装 / 页面渲染，不是 Vue 的同构 SSR[[Vue 同构SSR渲染]]。Node 服务端会渲染出完整 **HTML 骨架**，包括：
- Ocean Layout 的 DOM 容器，例如 #header 、#breadcrumb
- 子应该挂载点 #root
- 动态注入的 Layout 和子应用 CSS/JS
- 用户、菜单等登录态数据等
HTML 返回后，浏览器执行 Ocean Layout 和 Vue 子应用脚本，分别挂载 UI。因此首屏 HTML、鉴权数据、资源选择由服务端完成，但业务 Vue 组件仍是客户端运行和渲染。

这里的 Ocean Layout 和 Vue 子应用脚本指的是：挂载的 layout、子应用对应打包后的 JS 文件，主要完成一下事项：
```TS
HBS：提供容器、数据、资源标签
  ↓
Ocean Layout JS：准备统一外壳与事件监听
  ↓
子应用 vendor JS：提供 Vue 等依赖
  ↓
子应用 app JS：创建 Vue，挂到 #root
  ↓
App.vue 发送 SYSTEM_MOUNT
  ↓
Ocean Layout 渲染菜单、Header、Tab、面包屑，并同步子应用路由
```

## 三、主子应用通信机制

子应用和主应用（Layout）使用同一个发布订阅事件包，全局共享一个通信实例。通信实例的本质就是发布订阅事件实现。
#### 3.1 子应用的事件
##### 3.1.1 子应用订阅的事件
|事件|订阅位置|收到后做什么|
|---|---|---|
|`EVENT:LAYOUT_READY`|`App.vue` 的 `mounted`|当前只打印日志，表示 Ocean Layout 已完成初始化|
##### 3.1.2 子应用发布的事件
| 事件                    | 触发时机           | Layout 如何处理                        |
| --------------------- | -------------- | ---------------------------------- |
| `EVENT:SYSTEM_MOUNT`  | Vue 根应用挂载完成后   | Layout 开始渲染外壳，并接管/监听子应用路由          |
| `EVENT:CHANGE_TITLE`  | 子应用路由或页面标题变化   | Layout 设置浏览器标题                     |
| `EVENT:G_LAYOUT_FOLD` | 业务页面需要全屏/隐藏外壳时 | Layout 隐藏或恢复 Header、Sider、Tabs、面包屑 |
#### 3.2 主应用的事件
##### 3.2.1 主应用订阅的事件
| 事件                      | 发送方                            | Layout 的行为                    |
| ----------------------- | ------------------------------ | ----------------------------- |
| `EVENT:SYSTEM_MOUNT`    | 子应用                            | 初始化 Ocean 外壳；监听子应用路由          |
| `EVENT:LOCATION_CHANGE` | Layout 内的 Sider、Tabs、SubHeader | 跨子应用整页跳转；同子应用调用 `router.push` |
| `EVENT:CHANGE_TITLE`    | 子应用                            | 更新 `document.title`           |
| `EVENT:G_LAYOUT_FOLD`   | 子应用                            | 隐藏/显示 Layout 各区域              |
##### 3.2.2 主应用发布的事件
| 事件                      | 触发位置                       | 订阅者                               |
| ----------------------- | -------------------------- | --------------------------------- |
| `EVENT:LAYOUT_READY`    | Layout 初始化并渲染完成后           | 子应用                               |
| `EVENT:LOCATION_CHANGE` | Sider、Tabs、SubHeader 点击菜单时 | Layout 中控路由处理器                    |
| `LOCATION_CHANGED`      | 子应用 Router 发生变化后           | Header、Sider、Tabs、Breadcrumb、埋点模块 |
## 四、主子应用、子应用与子应用之间如何实现 CSS、JS 隔离

Ocean 没有实现 qiankun 式的 Proxy JS 沙箱或 Shadow DOM/CSS 重写隔离。它的核心策略是路由级页面隔离：一次服务端只组装一个子应用，跨子应用时整页跳转，旧页面随 Document 销毁，因此子应用之间通常不会长期共存和互相污染。

在同页的 Layout 与子应用之间，CSS 主要依赖 `#root` 挂载边界、命名约定和局部 scoped 样式，属于软隔离

**额外补充知识点**：浏览器是否缓存 CSS，主要由 CSS 响应头决定，而不是 HBS 里的 meta 标签。举例：`Cache-Control: max-age=3600` 此时浏览器会缓存当前的子应用的 CSS 文件，下次再切到该子应用时无需重新获取 CSS 文件
## 五、ocean 隔离机制
- **路由隔离**：每个子应用使用独立 context，如 `/new-house-admin/`
- **资源隔离**：每个子应用独立构建、独立 CDN/OSS 路径、独立 manifest
- **运行区域隔离**：业务应用只挂载在 `#root`；Ocean Layout 占据 Header、Sider、Breadcrumb 等固定容器。
- **页面级隔离**：通常一次只加载一个子应用；跨子应用路由时采用整页跳转，而非多个应用同时常驻
## 六、Ocean 微前端框架的优势

当时我们根据内部后台系统“单业务页运行、存量系统很多、统一权限和导航要求高”的场景，选择了服务端编排而不是重型客户端沙箱。**它牺牲了多子应用并行常驻的能力，换来了更低的接入成本、更强的服务端治理，以及对旧系统的兼容性**

- **低侵入迁移**：存量 Vue、React、甚至旧系统都只需要适配资源、路由前缀和事件协议；遗留系统还能使用 iframe。
- **平台化治理**：应用地址、manifest、加载顺序、灰度路径、Layout 开关、插件等由服务端配置管理，不需要改主应用代码。
- **性能与稳定性**：应用、资源、菜单、代理规则使用 Redis 缓存；Egg 同时拉取 Layout 和子应用 manifest，避免每次完全依赖数据库。
- **统一体验**：Header、菜单、面包屑、Tab、埋点、水印、意见反馈等由外壳统一注入，业务子应用只维护内
- ~~对接集团系统更加灵活例如： am系统，auth鉴权，听云等性能监控系统，水印组件，评分组件通过配置接入~~


## 七、关于其他微前端框架和乾坤的实现原理看 Notion