import {
  BlockfrostProvider,
  ForgeScript,
  MeshTxBuilder,
  deserializeAddress,
  resolveScriptHash,
  stringToHex,
} from "@meshsdk/core";
import { MeshCardanoHeadlessWallet, AddressType } from "@meshsdk/wallet";
import type { NativeScript } from "@meshsdk/core";

const BLOCKFROST_KEY = process.env.BLOCKFROST_KEY ?? "";
const MNEMONIC = process.env.MNEMONIC ?? "";

const NETWORK_ID = Number(process.env.NETWORK_ID ?? "0"); // 0=testnet (preprod/preview), 1=mainnet
const LOCK_SLOT = Number(process.env.LOCK_SLOT ?? "90000000");
const COLLECTION_SIZE = Number(process.env.COLLECTION_SIZE ?? "9");
const ASSET_NAME_PREFIX = process.env.ASSET_NAME_PREFIX ?? "WineLedger NFT #";
const IMAGE_IPFS =
  process.env.IMAGE_IPFS ??
  "ipfs://QmPS4PBvpGc2z6Dd6JdYqfHrKnURjtRGPTJWdhnAXNA8bQ";

if (!BLOCKFROST_KEY || !MNEMONIC) {
  throw new Error("Missing BLOCKFROST_KEY or MNEMONIC in environment");
}
if (![0, 1].includes(NETWORK_ID)) {
  throw new Error("NETWORK_ID must be 0 (testnet) or 1 (mainnet)");
}
if (!Number.isInteger(LOCK_SLOT) || LOCK_SLOT <= 0) {
  throw new Error("LOCK_SLOT must be a positive integer slot in the future");
}
if (!Number.isInteger(COLLECTION_SIZE) || COLLECTION_SIZE <= 0) {
  throw new Error("COLLECTION_SIZE must be a positive integer");
}
if (!IMAGE_IPFS.startsWith("ipfs://")) {
  throw new Error("IMAGE_IPFS must start with ipfs://");
}

type NFTMetadata = {
  name: string;
  image: string;
  mediaType: string;
  description?: string;
  attributes?: Record<string, unknown>;
  files?: Array<{ mediaType: string; name: string; src: string }>;
};

function createMetadata(
  name: string,
  imageIpfs: string,
  attributes?: Record<string, unknown>
): NFTMetadata {
  return {
    name,
    image: imageIpfs,
    mediaType: "image/png",
    description: `${name} from the WineLedger collection`,
    attributes,
    files: [{ mediaType: "image/png", name, src: imageIpfs }],
  };
}

async function main() {
  const provider = new BlockfrostProvider(BLOCKFROST_KEY);

  const wallet = await MeshCardanoHeadlessWallet.fromMnemonic({
    mnemonic: MNEMONIC.split(/\s+/).filter(Boolean),
    networkId: NETWORK_ID,
    walletAddressType: AddressType.Base,
    fetcher: provider,
    submitter: provider,
  });

  const address = await wallet.getChangeAddressBech32();
  const utxos = await wallet.getUtxosMesh();
  const { pubKeyHash } = deserializeAddress(address);

  console.log("Wallet:", address);
  console.log("UTxOs:", utxos.length);
  if (utxos.length === 0) {
    throw new Error("No UTxOs available. Fund the wallet first.");
  }
  if (!pubKeyHash) {
    throw new Error("Could not derive pubKeyHash from wallet address");
  }

  const nativeScript: NativeScript = {
    type: "all",
    scripts: [
      { type: "before", slot: LOCK_SLOT.toString() },
      { type: "sig", keyHash: pubKeyHash },
    ],
  };

  const forgingScript = ForgeScript.fromNativeScript(nativeScript);
  const policyId = resolveScriptHash(forgingScript);
  console.log("Policy ID:", policyId);

  const collectionMetadata: Record<string, Record<string, NFTMetadata>> = {
    [policyId]: {},
  };

  const txBuilder = new MeshTxBuilder({ fetcher: provider });
  for (let i = 1; i <= COLLECTION_SIZE; i++) {
    const tokenName = `${ASSET_NAME_PREFIX}${i}`;
    const tokenNameHex = stringToHex(tokenName);

    txBuilder.mint("1", policyId, tokenNameHex).mintingScript(forgingScript);

    collectionMetadata[policyId][tokenName] = createMetadata(tokenName, IMAGE_IPFS, {
      edition: i,
      collection_size: COLLECTION_SIZE,
    });
  }

  const unsignedTx = await txBuilder
    .metadataValue(721, collectionMetadata)
    .changeAddress(address)
    .invalidHereafter(LOCK_SLOT)
    .selectUtxosFrom(utxos)
    .complete();

  const signedTx = await wallet.signTx(unsignedTx, false);
  const txHash = await wallet.submitTx(signedTx);

  console.log("Transaction submitted!");
  console.log("Transaction hash:", txHash);
  console.log(`View on explorer: https://preprod.cardanoscan.io/transaction/${txHash}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

