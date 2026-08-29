import { createHash } from 'node:crypto';
import { access, readFile } from 'node:fs/promises';

const dist = new URL('../dist/', import.meta.url);
const required = [
  'index.html',
  'llms.txt',
  'llms-full.txt',
  'commands.json',
  'agent.json',
  'skills/datacore/SKILL.md',
  'skills/datacore-conductivity/SKILL.md',
  '.well-known/agent-skills/index.json',
  '.well-known/agent-skills/datacore.zip',
  '.well-known/agent-skills/datacore-conductivity.zip',
  '.well-known/skills/index.json',
  'CNAME',
  'robots.txt',
  'og.png',
];

for (const relative of required) {
  await access(new URL(relative, dist));
}

const commands = JSON.parse(await readFile(new URL('commands.json', dist), 'utf8'));
if (!Array.isArray(commands.commands) || commands.commands.length < 10) {
  throw new Error('commands.json does not contain the expected CLI command inventory');
}

const discovery = JSON.parse(
  await readFile(new URL('.well-known/agent-skills/index.json', dist), 'utf8'),
);
if (
  discovery.$schema !== 'https://schemas.agentskills.io/discovery/0.2.0/schema.json' ||
  !Array.isArray(discovery.skills) ||
  discovery.skills.length !== 2
) {
  throw new Error('Agent Skills discovery index is missing or invalid');
}
for (const skill of discovery.skills) {
  if (skill.type !== 'archive' || !/^sha256:[a-f0-9]{64}$/.test(skill.digest)) {
    throw new Error('Agent Skill archive metadata is invalid for ' + skill.name);
  }
  const archive = await readFile(new URL('.well-known/agent-skills/' + skill.url, dist));
  const digest = 'sha256:' + createHash('sha256').update(archive).digest('hex');
  if (digest !== skill.digest) {
    throw new Error('Agent Skill archive digest mismatch for ' + skill.name);
  }
}

const cname = (await readFile(new URL('CNAME', dist), 'utf8')).trim();
if (cname !== 'datacore-cli.dp.cd.mba') {
  throw new Error('CNAME is missing or invalid');
}

const llms = await readFile(new URL('llms.txt', dist), 'utf8');
for (const endpoint of [
  '/commands.json',
  '/skills/datacore/SKILL.md',
  '/.well-known/agent-skills/index.json',
]) {
  if (!llms.includes(endpoint)) {
    throw new Error('llms.txt does not link to ' + endpoint);
  }
}

console.log('Validated ' + required.length + ' published artifacts in ' + dist.pathname);
