import CryptoJS from "crypto-js";

// Usar una clave de encriptación desde variables de entorno
const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || "default-unsafe-key-change-in-production";

/**
 * Encripta un texto usando AES
 */
export function encryptText(text: string): string {
  return CryptoJS.AES.encrypt(text, ENCRYPTION_KEY).toString();
}

/**
 * Desencripta un texto usando AES
 */
export function decryptText(encryptedText: string): string {
  const bytes = CryptoJS.AES.decrypt(encryptedText, ENCRYPTION_KEY);
  return bytes.toString(CryptoJS.enc.Utf8);
}

/**
 * Valida que el texto desencriptado sea válido
 */
export function isValidEncryption(encryptedText: string): boolean {
  try {
    const decrypted = decryptText(encryptedText);
    return decrypted.length > 0;
  } catch {
    return false;
  }
}
