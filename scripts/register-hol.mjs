/**
 * Register Lamina agent in the Hashgraph Online (HOL) Registry.
 * Uses HCS-10 (OpenConvAI) and HCS-11 (Profile) standards.
 *
 * Run: node scripts/register-hol.mjs
 */

import { HCS10Client, AgentBuilder, AIAgentCapability } from '@hashgraphonline/standards-sdk';

const OPERATOR_ID = process.env.HEDERA_ACCOUNT_ID || '0.0.8003096';
const OPERATOR_KEY = process.env.HEDERA_PRIVATE_KEY || '';

if (!OPERATOR_KEY) {
  console.error('Set HEDERA_PRIVATE_KEY environment variable');
  process.exit(1);
}

// Strip 0x prefix if present
const privateKey = OPERATOR_KEY.startsWith('0x') ? OPERATOR_KEY.slice(2) : OPERATOR_KEY;

async function main() {
  console.log('Initializing HCS-10 client...');

  const client = new HCS10Client({
    network: 'testnet',
    operatorId: OPERATOR_ID,
    operatorPrivateKey: privateKey,
    logLevel: 'info',
  });

  console.log('Building agent profile...');

  const agentBuilder = new AgentBuilder()
    .setName('Lamina')
    .setDescription(
      'Autonomous RWA lifecycle management agent on Hedera. ' +
      'Manages tokenized bond issuance, compliance (KYC/OFAC), coupon distribution, ' +
      'NAV updates, regulatory reporting, and maturity settlement — all autonomously.'
    )
    .setAgentType('autonomous')
    .setCapabilities([
      AIAgentCapability.TEXT_GENERATION,
      AIAgentCapability.KNOWLEDGE_RETRIEVAL,
      AIAgentCapability.TRANSACTION_ANALYTICS,
      AIAgentCapability.API_INTEGRATION,
    ])
    .setModel('claude-haiku')
    .setNetwork('testnet')
    .setMetadata({
      creator: 'Lamina',
      version: '1.2.0',
      website: 'https://lamina-agent.vercel.app',
      github: 'https://github.com/Ni8crawler18/lamina',
    });

  console.log('Creating and registering agent...');

  const result = await client.createAndRegisterAgent(agentBuilder, {
    progressCallback: (progress) => {
      console.log(`  [${progress.stage}] ${progress.progressPercent}% — ${progress.detail || ''}`);
    },
  });

  if (result.success) {
    console.log('\n=== Agent Registered Successfully ===');
    console.log('Agent Account:', result.metadata?.accountId);
    console.log('Inbound Topic:', result.metadata?.inboundTopicId);
    console.log('Outbound Topic:', result.metadata?.outboundTopicId);
    console.log('Profile Topic:', result.metadata?.profileTopicId);
    console.log('Private Key:', result.metadata?.privateKey);
    console.log('\nSave these values in your .env file!');
  } else {
    console.error('Registration failed:', result.error || 'Unknown error');
  }
}

main().catch(console.error);
