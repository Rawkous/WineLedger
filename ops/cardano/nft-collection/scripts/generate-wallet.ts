import { MeshCardanoHeadlessWallet, AddressType } from "@meshsdk/wallet";
import { generateMnemonic } from "@meshsdk/core";

const NETWORK_ID = Number(process.env.NETWORK_ID ?? "0"); // 0=testnet (preprod/preview), 1=mainnet
if (![0, 1].includes(NETWORK_ID)) {
  throw new Error("NETWORK_ID must be 0 (testnet) or 1 (mainnet)");
}

const words = generateMnemonic(256);
console.log("Mnemonic phrase:");
console.log(words.join(" "));
console.log("");

const wallet = await MeshCardanoHeadlessWallet.fromMnemonic({
  mnemonic: words,
  networkId: NETWORK_ID,
  walletAddressType: AddressType.Base,
});

const address = await wallet.getChangeAddressBech32();
console.log("Wallet address:");
console.log(address);

