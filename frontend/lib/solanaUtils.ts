import { Connection, PublicKey, Transaction, TransactionInstruction } from "@solana/web3.js";

const MEMO_PROGRAM_ID = new PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr");

/**
 * Solana Memo 트랜잭션을 빌드합니다.
 * 전략 해시를 메모로 기록하여 온체인 증명.
 */
export async function buildMemoTransaction(
  connection: Connection,
  payer: PublicKey,
  memo: string,
): Promise<Transaction> {
  const tx = new Transaction();

  tx.add(
    new TransactionInstruction({
      keys: [{ pubkey: payer, isSigner: true, isWritable: true }],
      programId: MEMO_PROGRAM_ID,
      data: Buffer.from(memo, "utf-8"),
    }),
  );

  const { blockhash } = await connection.getLatestBlockhash();
  tx.recentBlockhash = blockhash;
  tx.feePayer = payer;

  return tx;
}

/**
 * 트랜잭션 확인 대기
 */
export async function confirmTransaction(
  connection: Connection,
  signature: string,
): Promise<boolean> {
  try {
    const result = await connection.confirmTransaction(signature, "confirmed");
    return !result.value.err;
  } catch {
    return false;
  }
}

/**
 * Solana Explorer URL 생성
 */
export function getExplorerUrl(signature: string, network: string = "devnet"): string {
  return `https://explorer.solana.com/tx/${signature}?cluster=${network}`;
}
