# WineLedger NFT collection minter (Mesh + native scripts)

This folder is a self-contained Bun + TypeScript tool to mint **multiple NFTs in one transaction** on Cardano using **native scripts** (no smart contracts) and **CIP-25** metadata.

## Prereqs

- Bun installed
- A Blockfrost API key (Preprod recommended)
- A funded wallet on the target network (testnet faucet for Preprod)

## Setup

```bash
cd ops/cardano/nft-collection
bun install
cp .env.example .env
```

Edit `.env`:

- `MNEMONIC`: 24 words (space-separated)
- `BLOCKFROST_KEY`: your Blockfrost key
- `LOCK_SLOT`: a slot **in the future** for the mint policy expiry

## Generate a wallet (optional)

```bash
bun run generate-wallet
```

Fund the printed address via the appropriate testnet faucet, then set the mnemonic/address in your `.env`.

## Mint the collection

```bash
bun run mint
```

The transaction mints `COLLECTION_SIZE` NFTs under a time-locked policy:

- `before`: valid only before `LOCK_SLOT`
- `sig`: requires your wallet signature

Metadata is attached at label `721` using a CIP-25 compatible shape:

```text
721: {
  <policyId>: {
    <assetName>: { name, image, ... }
  }
}
```

## Notes

- If you get `Slot has already passed`, increase `LOCK_SLOT`.
- If you get `Insufficient funds`, request more test ADA (each NFT increases min-UTxO).
- If the transaction is too large, reduce `COLLECTION_SIZE`.

