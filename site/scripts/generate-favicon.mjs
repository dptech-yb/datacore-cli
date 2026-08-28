import sharp from 'sharp';
import { fileURLToPath } from 'node:url';

const tile = Buffer.from(
  '<svg width="128" height="128" xmlns="http://www.w3.org/2000/svg">' +
    '<rect width="128" height="128" rx="30" fill="#2563eb"/>' +
    '<rect x="27" y="24" width="74" height="80" rx="18" fill="#0d1830"/>' +
    '<path d="M48 46h32M48 64h22M48 82h32" stroke="#e8f0ff" stroke-width="8" stroke-linecap="round"/>' +
  '</svg>'
);

await sharp(tile)
  .png()
  .toFile(fileURLToPath(new URL('../public/favicon.png', import.meta.url)));
