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

const cname = (await readFile(new URL('CNAME', dist), 'utf8')).trim();
if (cname !== 'datacore-cli.dp.cd.mba') {
  throw new Error('CNAME is missing or invalid');
}

const llms = await readFile(new URL('llms.txt', dist), 'utf8');
for (const endpoint of ['/commands.json', '/skills/datacore/SKILL.md']) {
  if (!llms.includes(endpoint)) {
    throw new Error('llms.txt does not link to ' + endpoint);
  }
}

console.log('Validated ' + required.length + ' published artifacts in ' + dist.pathname);
