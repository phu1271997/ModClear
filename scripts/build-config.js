const fs = require('fs');
const path = require('path');

// Load environment variables locally if .env exists
try {
  const envPath = path.join(__dirname, '../.env');
  if (fs.existsSync(envPath)) {
    const envFile = fs.readFileSync(envPath, 'utf8');
    envFile.split('\n').forEach(line => {
      // Ignore comments and empty lines
      if (!line.trim() || line.trim().startsWith('#')) return;
      const parts = line.split('=');
      if (parts.length >= 2) {
        const key = parts[0].trim();
        const value = parts.slice(1).join('=').trim();
        process.env[key] = value;
      }
    });
  }
} catch (e) {
  console.log('No local .env found or failed to parse:', e.message);
}

const contractAddress = process.env.GENLAYER_CONTRACT_ADDRESS || '0xF5e7CCc1708f49A94729AeDb501a966606e33662';
const chain = process.env.GENLAYER_CHAIN || 'studio';

const configContent = `// Auto-generated configuration. Do not edit directly.
export const CONTRACT_ADDRESS = "${contractAddress}";
export const CHAIN = "${chain}";
`;

const destPath = path.join(__dirname, '../frontend/src/config.js');
// Ensure parent directories exist
fs.mkdirSync(path.dirname(destPath), { recursive: true });
fs.writeFileSync(destPath, configContent, 'utf8');
console.log(`Generated config.js with CONTRACT_ADDRESS=${contractAddress}, CHAIN=${chain}`);
