package com.regevidencehub.waste

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BuildConfigurationTest {
    @Test fun productionIdentityAndEndpointAreWasteSpecific() {
        assertEquals("com.regevidencehub.waste", BuildConfig.APPLICATION_ID)
        assertTrue(BuildConfig.API_BASE_URL.startsWith("https://") || BuildConfig.API_BASE_URL == "http://127.0.0.1:8765")
    }
}
