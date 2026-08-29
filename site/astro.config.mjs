// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import starlight from '@astrojs/starlight';

export default defineConfig({
	site: 'https://datacore-cli.dp.cd.mba',
	integrations: [
		sitemap(),
		starlight({
			title: 'DataCore CLI',
			description: '从终端与 AI Agent 安全调用 DataCore 工作流',
			defaultLocale: 'root',
			locales: { root: { label: '简体中文', lang: 'zh-CN' } },
			lastUpdated: true,
			favicon: '/favicon.png',
			logo: {
				src: './src/assets/datacore-logo.png',
				alt: 'DataCore',
				replacesTitle: false,
			},
			customCss: ['./src/styles/custom.css'],
			social: [
				{ icon: 'external', label: '打开 DataCore 平台', href: 'https://datacore.dp.qifalab.cn/' },
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/dptech-yb/datacore-cli' },
			],
			head: [
				{ tag: 'meta', attrs: { name: 'theme-color', content: '#0d1830' } },
				{ tag: 'meta', attrs: { property: 'og:title', content: 'DataCore CLI' } },
				{
					tag: 'meta',
					attrs: {
						property: 'og:description',
						content: '安装 CLI 与 Agent Skills，从终端、脚本或 AI Agent 安全调用 DataCore 工作流',
					},
				},
				{
					tag: 'meta',
					attrs: {
						property: 'og:image',
						content: 'https://datacore-cli.dp.cd.mba/og.png',
					},
				},
				{ tag: 'meta', attrs: { property: 'og:type', content: 'website' } },
				{ tag: 'meta', attrs: { name: 'twitter:card', content: 'summary_large_image' } },
				{ tag: 'meta', attrs: { name: 'twitter:title', content: 'DataCore CLI' } },
				{
					tag: 'meta',
					attrs: {
						name: 'twitter:description',
						content: '安装 CLI 与 Agent Skills，从终端、脚本或 AI Agent 安全调用 DataCore 工作流',
					},
				},
				{
					tag: 'meta',
					attrs: {
						name: 'twitter:image',
						content: 'https://datacore-cli.dp.cd.mba/og.png',
					},
				},
				{
					tag: 'script',
					attrs: { type: 'application/ld+json' },
					content: JSON.stringify({
						'@context': 'https://schema.org',
						'@type': 'SoftwareApplication',
						name: 'DataCore CLI',
						applicationCategory: 'DeveloperApplication',
						operatingSystem: 'Windows, macOS, Linux',
						softwareVersion: '0.2.0',
						url: 'https://datacore-cli.dp.cd.mba/',
						codeRepository: 'https://github.com/dptech-yb/datacore-cli',
					}),
				},
			],
			editLink: {
				baseUrl: 'https://github.com/dptech-yb/datacore-cli/edit/main/site/',
			},
			sidebar: [
				{
					label: '开始使用',
					items: [
						{ label: '安装与快速开始', slug: 'getting-started/install' },
						{ label: '身份、授权与权限', slug: 'getting-started/authentication' },
					],
				},
				{
					label: '按场景使用',
					items: [
						{ label: '全平台能力', slug: 'workflows/platform' },
						{ label: '第三方 Agent 接入', slug: 'agents' },
						{ label: '电导率预测迭代', slug: 'workflows/conductivity' },
					],
				},
				{
					label: '参考',
					items: [
						{ label: 'CLI 命令', slug: 'reference/commands' },
						{ label: '结构化输出', slug: 'reference/output-contract' },
						{ label: '故障恢复', slug: 'troubleshooting' },
						{ label: '安全与发布可信度', slug: 'security' },
					],
				},
				{
					label: '相关入口',
					collapsed: false,
					items: [
						{
							label: '打开 DataCore 平台 ↗',
							link: 'https://datacore.dp.qifalab.cn/',
							attrs: { target: '_blank', rel: 'noopener noreferrer' },
						},
						{
							label: 'GitHub 仓库 ↗',
							link: 'https://github.com/dptech-yb/datacore-cli',
							attrs: { target: '_blank', rel: 'noopener noreferrer' },
						},
					],
				},
			],
		}),
	],
});
