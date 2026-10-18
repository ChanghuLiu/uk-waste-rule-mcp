package com.regevidencehub.waste

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Encrypts the Play token with a non-exportable Android Keystore key for recovery. */
internal object PurchaseVault {
    private const val PREFS = "waste_play_recovery"
    private const val ALIAS = "waste_play_recovery_v1"
    private const val CASE_REF = "case_ref"
    private const val TOKEN = "purchase_token_ciphertext"

    fun caseRef(context: Context): String = prefs(context).getString(CASE_REF, "").orEmpty()

    fun token(context: Context): String? {
        return try {
            val packed = prefs(context).getString(TOKEN, null) ?: return null
            val bytes = Base64.decode(packed, Base64.NO_WRAP)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(0, 12)))
            cipher.doFinal(bytes.copyOfRange(12, bytes.size)).toString(Charsets.UTF_8)
        } catch (_: Exception) { null }
    }

    fun setCase(context: Context, caseRef: String) {
        val store = prefs(context)
        if (store.getString(CASE_REF, "") != caseRef) {
            store.edit().remove(TOKEN).putString(CASE_REF, caseRef).apply()
        }
    }

    fun clear(context: Context) { prefs(context).edit().remove(CASE_REF).remove(TOKEN).apply() }

    fun save(context: Context, caseRef: String, token: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val sealed = cipher.iv + cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        prefs(context).edit().putString(CASE_REF, caseRef)
            .putString(TOKEN, Base64.encodeToString(sealed, Base64.NO_WRAP)).apply()
    }

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setRandomizedEncryptionRequired(true)
            .build())
        return generator.generateKey()
    }
}
