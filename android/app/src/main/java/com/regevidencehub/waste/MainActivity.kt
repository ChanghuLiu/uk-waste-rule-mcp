package com.regevidencehub.waste

import android.app.Activity
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.foundation.Image
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.android.billingclient.api.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

private const val PRODUCT_ID = "waste_report_one"
private fun request(path: String, body: JSONObject? = null): JSONObject {
    val c = URL(BuildConfig.API_BASE_URL.trimEnd('/') + path).openConnection() as HttpURLConnection
    c.connectTimeout = 6000; c.readTimeout = 15000; c.requestMethod = if (body == null) "GET" else "POST"
    if (body != null) { c.doOutput = true; c.setRequestProperty("Content-Type", "application/json"); c.outputStream.use { it.write(body.toString().toByteArray()) } }
    val code = c.responseCode
    val stream = if (code in 200..299) c.inputStream else c.errorStream
    val payload = stream?.bufferedReader()?.use { it.readText() }.orEmpty(); c.disconnect()
    if (code !in 200..299) throw IOException("Mobile service request failed ($code): $payload")
    return JSONObject(payload)
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContent { WasteApp() } }
}

private data class Question(val id: String, val title: String, val type: String, val options: List<Pair<String,String>>)
private data class SavedItem(val title: String, val detail: String)
private enum class Page { HOME, CHECKS, REPORTS, WIZARD, RESULT, OFFER, REPORT }

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun WasteApp() {
    val context = LocalContext.current
    val activity = context as Activity
    val scope = rememberCoroutineScope()
    val prefs = remember { context.getSharedPreferences("waste_mobile", 0) }
    var page by remember { mutableStateOf(Page.HOME) }
    var tab by remember { mutableStateOf("Home") }
    var answers by remember { mutableStateOf(JSONObject().put("nation", "England")) }
    var question by remember { mutableStateOf<Question?>(null) }
    var startQuestions by remember { mutableStateOf<Map<String,Question>>(emptyMap()) }
    var answerText by remember { mutableStateOf("") }
    var selected by remember { mutableStateOf(setOf<String>()) }
    var caseRef by remember { mutableStateOf(prefs.getString("case_ref", "").orEmpty()) }
    var result by remember { mutableStateOf<JSONObject?>(null) }
    var report by remember { mutableStateOf<JSONObject?>(null) }
    var statusText by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var billingMessage by remember { mutableStateOf("") }
    var product by remember { mutableStateOf<ProductDetails?>(null) }
    var billingAvailable by remember { mutableStateOf(false) }
    var backendVerifierAvailable by remember { mutableStateOf(false) }
    var checks by remember { mutableStateOf(prefs.getString("checks", "[]").orEmpty()) }
    var reports by remember { mutableStateOf(prefs.getString("reports", "[]").orEmpty()) }

    fun saveReport(value: JSONObject) {
        report = value
        val list = runCatching { JSONArray(reports) }.getOrElse { JSONArray() }
        list.put(0, value)
        reports = list.toString(); prefs.edit().putString("reports", reports).apply()
        page = Page.REPORT
    }
    fun beginServerQuestions() {
        scope.launch {
            busy = true
            try {
                val response = withContext(Dispatchers.IO) { request("/api/mobile/v1/readiness", answers) }
                val descriptor = response.optJSONObject("next_question")
                if (descriptor != null) {
                    question = Question(descriptor.optString("id"), descriptor.optString("title"), descriptor.optString("type"), jsonOptions(descriptor.optJSONArray("options")))
                    answerText = ""; selected = setOf(); page = Page.WIZARD
                } else {
                    result = response.optJSONObject("result") ?: JSONObject()
                    caseRef = response.optString("case_ref")
                    if (caseRef.isNotBlank()) prefs.edit().putString("case_ref", caseRef).apply()
                    statusText = response.optString("status")
                    val history = JSONArray(checks); history.put(0, JSONObject().put("title", result?.optString("title")).put("detail", result?.optString("message")))
                    checks = history.toString(); prefs.edit().putString("checks", checks).apply()
                    page = Page.RESULT
                }
            } catch (_: Exception) { statusText = "We couldn’t complete this check. No route was guessed."; result = null; page = Page.RESULT }
            finally { busy = false }
        }
    }
    fun finishUnknown(field: String) {
        scope.launch {
            busy = true; caseRef = ""
            try {
                val body = JSONObject(answers.toString()).put("stop_on_missing", field)
                val response = withContext(Dispatchers.IO) { request("/api/mobile/v1/readiness", body) }
                result = response.optJSONObject("result") ?: JSONObject()
                statusText = response.optString("status")
                page = Page.RESULT
            } catch (_: Exception) { statusText = "We couldn’t complete this check. No route was guessed."; result = null; page = Page.RESULT }
            finally { busy = false }
        }
    }
    fun sendPurchase(p: Purchase) {
        if (p.purchaseState == Purchase.PurchaseState.PENDING) { billingMessage = "Google Play is processing your purchase. Your report will unlock when it is confirmed."; return }
        if (p.purchaseState != Purchase.PurchaseState.PURCHASED || !p.products.contains(PRODUCT_ID)) return
        val purchaseCase = PurchaseVault.caseRef(context)
        if (purchaseCase.isBlank()) { billingMessage = "Open the free check linked to this purchase, then restore it."; return }
        scope.launch {
            busy = true
            try {
                PurchaseVault.save(context, purchaseCase, p.purchaseToken)
                val body = JSONObject().put("case_ref", purchaseCase).put("purchase_token", p.purchaseToken)
                val unlocked = withContext(Dispatchers.IO) { request("/api/mobile/v1/play/redeem", body) }
                if (unlocked.optBoolean("report_granted")) {
                    val r = unlocked.optJSONObject("report") ?: JSONObject()
                    report = r; val list = JSONArray(reports); list.put(0, r); reports = list.toString(); prefs.edit().putString("reports", reports).apply()
                    if (!unlocked.optBoolean("consume_pending")) PurchaseVault.clear(context)
                    page = Page.REPORT; billingMessage = if (unlocked.optBoolean("consume_pending")) "Report ready. Google Play will finish processing shortly." else "Your report is ready."
                } else billingMessage = "We couldn’t verify this purchase yet. Your free check is saved."
            } catch (_: Exception) { billingMessage = "We couldn’t verify this purchase yet. Keep this check open and try Restore purchase." }
            finally { busy = false }
        }
    }
    val listener = remember { PurchasesUpdatedListener { r, purchases ->
        when (r.responseCode) {
            BillingClient.BillingResponseCode.OK -> purchases.orEmpty().firstOrNull { PRODUCT_ID in it.products }?.let(::sendPurchase)
            BillingClient.BillingResponseCode.USER_CANCELED -> billingMessage = "Purchase cancelled. No charge was made."
            else -> billingMessage = "Google Play purchase is temporarily unavailable. Your free check is unaffected."
        }
    } }
    val billing = remember { BillingClient.newBuilder(context.applicationContext).setListener(listener).enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build()).enableAutoServiceReconnection().build() }

    LaunchedEffect(Unit) {
        try {
            val caps = withContext(Dispatchers.IO) { request("/api/mobile/v1/capabilities") }
            startQuestions = jsonOptions(caps.optJSONArray("questions")).associate { (id, _) -> id to questionFromDescriptor(caps.optJSONArray("questions"), id) }
            backendVerifierAvailable = caps.optJSONObject("play_billing")?.optBoolean("available") == true
        } catch (_: Exception) { statusText = "The service is temporarily unavailable." }
        billing.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(r: BillingResult) {
                if (r.responseCode != BillingClient.BillingResponseCode.OK) return
                billingAvailable = true
                val qp = QueryProductDetailsParams.Product.newBuilder().setProductId(PRODUCT_ID).setProductType(BillingClient.ProductType.INAPP).build()
                billing.queryProductDetailsAsync(QueryProductDetailsParams.newBuilder().setProductList(listOf(qp)).build()) { qr, details ->
                    product = if (qr.responseCode == BillingClient.BillingResponseCode.OK) details.productDetailsList.firstOrNull() else null
                }
                billing.queryPurchasesAsync(QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.INAPP).build()) { qr, purchases ->
                    if (qr.responseCode == BillingClient.BillingResponseCode.OK && caseRef.isNotBlank()) purchases.firstOrNull { PRODUCT_ID in it.products }?.let(::sendPurchase)
                }
            }
            override fun onBillingServiceDisconnected() { billingAvailable = false }
        })
        val oldCase = PurchaseVault.caseRef(context)
        val oldToken = PurchaseVault.token(context)
        if (oldCase.isNotBlank() && !oldToken.isNullOrBlank()) try {
            val recovered = withContext(Dispatchers.IO) { request("/api/mobile/v1/report/recover", JSONObject().put("case_ref", oldCase).put("purchase_token", oldToken)) }
            if (recovered.optBoolean("report_granted")) { report = recovered.optJSONObject("report"); if (!recovered.optBoolean("consume_pending")) PurchaseVault.clear(context); page = Page.HOME }
        } catch (_: Exception) { }
    }

    val dark = isSystemInDarkTheme()
    val light = lightColorScheme(primary = Color(0xFF37685B), onPrimary = Color.White, primaryContainer = Color(0xFFE1EFE7), onPrimaryContainer = Color(0xFF183D32), secondaryContainer = Color(0xFFE8EEE9), surface = Color(0xFFFAF9F6))
    val night = darkColorScheme(primary = Color(0xFFA2CDBB), onPrimary = Color(0xFF173D34), primaryContainer = Color(0xFF284C40), onPrimaryContainer = Color(0xFFD8EDE2), surface = Color(0xFF171A17))
    MaterialTheme(colorScheme = if (dark) night else light, shapes = Shapes(small = RoundedCornerShape(12.dp), medium = RoundedCornerShape(20.dp), large = RoundedCornerShape(28.dp))) {
        Scaffold(topBar = { TopAppBar(title = { Text("Waste preflight", fontWeight = FontWeight.SemiBold) }) }, bottomBar = {
            if (page in listOf(Page.HOME, Page.CHECKS, Page.REPORTS)) NavigationBar {
                listOf("Home", "Checks", "Reports").forEach { label -> NavigationBarItem(selected = tab == label, onClick = { tab = label; page = when(label){"Checks"->Page.CHECKS;"Reports"->Page.REPORTS;else->Page.HOME} }, icon = { Text(when(label){"Home"->"⌂";"Checks"->"✓";else->"▤"}) }, label = { Text(label) }) }
            }
        }) { inset ->
            Column(Modifier.fillMaxSize().padding(inset).imePadding().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp, vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                when (page) {
                    Page.HOME -> {
                        Text("A clearer next step for your waste operation", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                        Text("Check the route and evidence readiness using your facts.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { AssistChip(onClick = {}, label = { Text("Free check") }); AssistChip(onClick = {}, label = { Text("England") }); AssistChip(onClick = {}, label = { Text("No account") }) }
                        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) { Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) { Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)){ Image(painterResource(R.drawable.ic_waste_readiness),contentDescription="Waste readiness",modifier=Modifier.size(44.dp)); Column { Text("Start with your location, role and activity", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold); Text("A guided route check",style=MaterialTheme.typography.bodySmall) } }; Text("We’ll ask only for facts the check needs. Regulatory routing stays with the service."); Button(onClick = { answers = JSONObject(); caseRef=""; question = startQuestions["nation"]; answerText=""; selected=setOf(); page=Page.WIZARD }, enabled=startQuestions["nation"]!=null, modifier=Modifier.fillMaxWidth()) { Text("Start free check") } } }
                        Text("Route selection, registration, permit change and receiving site readiness.", style = MaterialTheme.typography.bodySmall)
                        Text("Preflight only. It does not issue permits, registrations or approvals.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Page.WIZARD -> Wizard(question, answerText, selected, busy, onText={answerText=it}, onSelected={selected=it}, onUnknown={ q -> finishUnknown(q) }, onBack={page=Page.HOME}, onContinue={
                        val q=question ?: return@Wizard
                        when(q.id) {
                            "nation" -> { answers.put("nation", selected.firstOrNull() ?: return@Wizard); beginServerQuestions() }
                            "role" -> { answers.put("role", selected.firstOrNull() ?: return@Wizard); beginServerQuestions() }
                            "activities" -> { if(selected.isEmpty()) return@Wizard; answers.put("activities", JSONArray(selected.toList())); beginServerQuestions() }
                            else -> { when(q.id){"hazardous_status"->answers.put(q.id,answerText=="true");"waste_types"->answers.put(q.id,JSONArray(answerText.split(",").map(String::trim).filter(String::isNotBlank)));else->answers.put(q.id,answerText)}; beginServerQuestions() }
                        }
                    })
                    Page.RESULT -> ResultPage(result, caseRef.isNotBlank(), onReport={page=Page.OFFER}, onHome={page=Page.HOME})
                    Page.OFFER -> {
                        Text("Your evidence report", style=MaterialTheme.typography.headlineSmall, fontWeight=FontWeight.Bold)
                        Text("One-time access for 24 hours. The localized Google Play price is shown below.", color=MaterialTheme.colorScheme.onSurfaceVariant)
                        Card { Column(Modifier.padding(20.dp), verticalArrangement=Arrangement.spacedBy(12.dp)) { Text("Includes the structured route result, findings, source references and next actions when available."); HorizontalDivider(); Text(product?.oneTimePurchaseOfferDetails?.formattedPrice ?: "Price unavailable", style=MaterialTheme.typography.titleLarge, fontWeight=FontWeight.Bold); if(!billingAvailable || !backendVerifierAvailable || product==null) Text("Google Play purchase is unavailable right now. Your free check remains available.", color=MaterialTheme.colorScheme.error); Button(enabled=product!=null && billingAvailable && backendVerifierAvailable && !busy, onClick={ val d=product ?: return@Button; val previousCase=PurchaseVault.caseRef(context); if(previousCase.isNotBlank() && previousCase!=caseRef && !PurchaseVault.token(context).isNullOrBlank()){ billingMessage="Restore the previous report before starting another purchase."; return@Button }; PurchaseVault.setCase(context,caseRef); val pp=BillingFlowParams.ProductDetailsParams.newBuilder().setProductDetails(d).build(); billing.launchBillingFlow(activity, BillingFlowParams.newBuilder().setProductDetailsParamsList(listOf(pp)).build()) }, modifier=Modifier.fillMaxWidth()) { Text("Continue with Google Play") }; OutlinedButton(onClick={
                            val savedCase=PurchaseVault.caseRef(context); val savedToken=PurchaseVault.token(context)
                            if(savedCase.isNotBlank() && !savedToken.isNullOrBlank()) scope.launch { try { busy=true; val rr=withContext(Dispatchers.IO){request("/api/mobile/v1/play/redeem",JSONObject().put("case_ref",savedCase).put("purchase_token",savedToken))}; if(rr.optBoolean("report_granted")) {val r=rr.optJSONObject("report"); report=r; if(r!=null){val stored=JSONArray(reports);stored.put(0,r);reports=stored.toString();prefs.edit().putString("reports",reports).apply()};if(!rr.optBoolean("consume_pending"))PurchaseVault.clear(context);page=Page.REPORT} else billingMessage="No recoverable purchase was found for this check." } catch (_:Exception){ billingMessage="Restore is temporarily unavailable." } finally{busy=false} }
                        }, modifier=Modifier.fillMaxWidth()) { Text("Restore purchase") }; if(billingMessage.isNotBlank()) Text(billingMessage) } }
                        TextButton(onClick={page=Page.RESULT}) { Text("Back to result") }
                    }
                    Page.REPORT -> ReportPage(report, onBack={page=Page.REPORTS})
                    Page.CHECKS -> { Text("Recent checks", style=MaterialTheme.typography.headlineSmall); Text("Saved on this device. Historical checks are view only."); val list=runCatching{JSONArray(checks)}.getOrElse{JSONArray()}; if(list.length()==0) EmptyMessage("Your completed checks will appear here."); for(i in 0 until list.length()) { val o=list.optJSONObject(i) ?: continue; SummaryCard(o.optString("title"), o.optString("detail")) } }
                    Page.REPORTS -> { Text("Reports", style=MaterialTheme.typography.headlineSmall); val list=runCatching{JSONArray(reports)}.getOrElse{JSONArray()}; if(list.length()==0) EmptyMessage("No saved reports yet. Your free check is always available."); for(i in 0 until list.length()) { val o=list.optJSONObject(i) ?: continue; SummaryCard("Evidence report", "England waste preflight report"); TextButton(onClick={report=o;page=Page.REPORT}){Text("Open saved report")} } }
                }
            }
        }
    }

}

private fun jsonOptions(items: JSONArray?): List<Pair<String,String>> = if (items == null) emptyList() else (0 until items.length()).mapNotNull { i -> items.optJSONObject(i)?.let { it.optString("id") to it.optString("label") } }
private fun questionFromDescriptor(items: JSONArray?, id: String): Question {
    val o = (0 until (items?.length() ?: 0)).mapNotNull { items?.optJSONObject(it) }.first { it.optString("id") == id }
    return Question(id, o.optString("title"), o.optString("type"), jsonOptions(o.optJSONArray("options")))
}

@Composable
private fun Wizard(q: Question?, text: String, selected: Set<String>, busy: Boolean, onText: (String)->Unit, onSelected: (Set<String>)->Unit, onUnknown: (String)->Unit, onBack: ()->Unit, onContinue: ()->Unit) {
    if (q == null) { Text("Loading the next question…"); return }
    Text("Your route check", style=MaterialTheme.typography.titleSmall, color=MaterialTheme.colorScheme.primary)
    LinearProgressIndicator(progress={ if(q.id in setOf("role","activities")) .3f else .7f }, modifier=Modifier.fillMaxWidth())
    Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(22.dp), verticalArrangement=Arrangement.spacedBy(14.dp)) {
        Text(q.title, style=MaterialTheme.typography.headlineSmall, fontWeight=FontWeight.SemiBold)
        when(q.type) {
            "single_choice" -> q.options.forEach { (id,label) -> Row(Modifier.fillMaxWidth().clickable { onSelected(setOf(id)); onText(id) }.heightIn(min=52.dp), verticalAlignment=Alignment.CenterVertically) { RadioButton(id in selected, { onSelected(setOf(id)); onText(id) }); Text(label) } }
            "multi_choice" -> q.options.forEach { (id,label) -> Row(Modifier.fillMaxWidth().clickable { onSelected(if(id in selected) selected-id else selected+id) }.heightIn(min=52.dp), verticalAlignment=Alignment.CenterVertically) { Checkbox(id in selected, { onSelected(if(id in selected) selected-id else selected+id) }); Text(label) } }
            else -> OutlinedTextField(text,onText,Modifier.fillMaxWidth(),label={Text("Your answer")},keyboardOptions=KeyboardOptions(keyboardType=if(q.id=="waste_types") KeyboardType.Text else KeyboardType.Text),minLines=2)
        }
        if(q.id=="hazardous_status") Text("If you don’t know, pause and confirm the facts. We won’t infer hazardous status.", style=MaterialTheme.typography.bodySmall)
    } }
    Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.spacedBy(12.dp)) { OutlinedButton(onBack,Modifier.weight(1f).height(50.dp)){Text("Back")}; Button(onContinue,Modifier.weight(1f).height(50.dp),enabled=!busy && (selected.isNotEmpty() || text.isNotBlank())){Text(if(busy) "Checking…" else "Continue")} }
    TextButton(onClick={onUnknown(q.id)},enabled=!busy,modifier=Modifier.fillMaxWidth()){Text("I don’t know yet")}
}

@Composable private fun ResultPage(result: JSONObject?, canReport: Boolean, onReport: ()->Unit, onHome: ()->Unit) {
    Text("Your check", style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold)
    if(result==null) { StatusCard("Current source not verified", "We couldn’t verify the current source state. Try again later.") }
    else {
        StatusCard(result.optString("title","Review needed"),result.optString("message"))
        InfoCard("Supported route",humanize(result.optString("route")))
        val findings=result.optJSONArray("findings")
        if(findings!=null) for(i in 0 until findings.length()) findings.optJSONObject(i)?.let { InfoCard(humanize(it.optString("severity")),it.optString("message")) }
        result.optJSONArray("next_actions")?.let { for(i in 0 until it.length()) Text("• ${it.optString(i)}", style=MaterialTheme.typography.bodyMedium) }
    }
    Text("Preflight only. This is not a compliance finding, permit or registration decision, regulator approval or legal advice.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
    if(canReport) Button(onReport,Modifier.fillMaxWidth()){Text("View report option")}
    TextButton(onHome,Modifier.fillMaxWidth()){Text("Back to Home")}
}

@Composable private fun ReportPage(report: JSONObject?, onBack: ()->Unit) {
    Text("Evidence report",style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold)
    if(report==null){EmptyMessage("This report is not available on this device.");return}
    val decision=report.optJSONObject("decision")
    if(decision!=null) { InfoCard("Route",humanize(decision.optString("route"))); InfoCard("Status",humanize(decision.optString("status"))); InfoCard("Summary",decision.optString("conclusion")) }
    report.optJSONArray("findings")?.let { a-> for(i in 0 until a.length()) a.optJSONObject(i)?.let { InfoCard(humanize(it.optString("severity")),it.optString("message")) } }
    report.optJSONArray("evidence")?.let { a-> if(a.length()>0) Text("Source references",style=MaterialTheme.typography.titleMedium); for(i in 0 until a.length()) a.optJSONObject(i)?.let { InfoCard(it.optString("title",it.optString("id")),it.optString("url")+" · checked "+it.optString("last_checked")) } }
    Text("Preflight information only; not a permit, registration, regulator approval or legal advice.",style=MaterialTheme.typography.bodySmall)
    OutlinedButton(onBack,Modifier.fillMaxWidth()){Text("Back to Reports")}
}

@Composable private fun StatusCard(title:String,message:String) { Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.primaryContainer)){Column(Modifier.padding(18.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){Text(title,style=MaterialTheme.typography.titleLarge,fontWeight=FontWeight.SemiBold);Text(message)}} }
@Composable private fun InfoCard(title:String,message:String) { Card(Modifier.fillMaxWidth()){Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(5.dp)){Text(title,style=MaterialTheme.typography.labelLarge,color=MaterialTheme.colorScheme.primary);Text(message)}} }
@Composable private fun SummaryCard(title:String,detail:String) { Card(Modifier.fillMaxWidth()){Column(Modifier.padding(16.dp)){Text(title,fontWeight=FontWeight.SemiBold);Text(detail,style=MaterialTheme.typography.bodySmall)}} }
@Composable private fun EmptyMessage(message:String) { Card(Modifier.fillMaxWidth()){Text(message,Modifier.padding(18.dp),color=MaterialTheme.colorScheme.onSurfaceVariant)} }
private fun humanize(s:String)=s.lowercase().replace('_',' ').replaceFirstChar { it.uppercase() }
