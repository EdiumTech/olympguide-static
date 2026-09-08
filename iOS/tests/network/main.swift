import Foundation

private func expect(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() { fatalError(message) }
}

private func expectFailure<T>(
    _ result: Result<T, NetworkError>,
    _ message: String,
    matching: (NetworkError) -> Bool
) {
    guard case .failure(let error) = result, matching(error) else { fatalError(message) }
}

let base = APIConfiguration.validatedBaseURL("https://api.olympguide.ru/api/v1")!
let catalogURL = APIConfiguration.url(for: "/universities", queryItems: nil, baseURL: base)!
expect(catalogURL.absoluteString == "https://api.olympguide.ru/api/v1/universities", "Preserve API prefix")

let trailingBase = APIConfiguration.validatedBaseURL("https://api.olympguide.ru/api/v1/")!
expect(APIConfiguration.url(for: "/universities", queryItems: nil, baseURL: trailingBase) == catalogURL,
       "Normalize trailing slash")
let rootBase = APIConfiguration.validatedBaseURL("https://api.olympguide.ru")!
expect(APIConfiguration.url(for: "/healthz", queryItems: nil, baseURL: rootBase)?.path == "/healthz",
       "Do not create a double slash for a root base URL")

let search = "Математика & физика"
let searchURL = APIConfiguration.url(
    for: "/olympiads", queryItems: [URLQueryItem(name: "search", value: search)], baseURL: base
)!
expect(URLComponents(url: searchURL, resolvingAgainstBaseURL: false)?.queryItems?.first?.value == search,
       "Encode Cyrillic and query separators")
for invalid in ["", "$(BASE_URL)", "http://api.olympguide.ru/api/v1", "https:/api.olympguide.ru/api/v1",
                "https://user:password@api.olympguide.ru/api/v1", "https://api.olympguide.ru/api/v1?x=1",
                "https://api.olympguide.ru/api/v1#fragment"] {
    expect(APIConfiguration.validatedBaseURL(invalid) == nil, "Reject invalid or insecure base URL")
}
for endpoint in ["universities", "//other.example/universities", "https://other.example",
                 "/universities?x=1", "/universities#fragment"] {
    expect(APIConfiguration.url(for: endpoint, queryItems: nil, baseURL: base) == nil,
           "Require API path and separate query items")
}

// check-session omits `type`; protected routes return it. Neither may decode as success.
for body in [nil, Data(), Data(#"{"message":"Unauthorized"}"#.utf8),
             Data(#"{"message":"Unauthorized","type":"Unauthorized"}"#.utf8)] as [Data?] {
    let result: Result<[Int], NetworkError> = HTTPResponseDecoder.decode(data: body, statusCode: 401)
    expectFailure(result, "401 must be an auth error, independent of the expected model") {
        if case .unauthorized = $0 { return true }; return false
    }
}

for body in [nil, Data(), Data("<html>Bad Gateway</html>".utf8)] as [Data?] {
    let result: Result<BaseServerResponse, NetworkError> = HTTPResponseDecoder.decode(data: body, statusCode: 502)
    expectFailure(result, "A proxy failure must never become an empty success or decoding error") {
        if case .internalServerError = $0 { return true }; return false
    }
}

let profile: Result<[Int], NetworkError> = HTTPResponseDecoder.decode(
    data: Data(#"{"type":"ProfileNotComplete","message":"Profile not complete"}"#.utf8), statusCode: 403
)
expectFailure(profile, "Decode the error envelope even when success expects an array") {
    if case .profileNotComplete = $0 { return true }; return false
}

let expired: Result<BaseServerResponse, NetworkError> = HTTPResponseDecoder.decode(
    data: Data(#"{"type":"PreviousCodeNotExpired","ttl":42}"#.utf8), statusCode: 400
)
expectFailure(expired, "Preserve the email code retry timer") {
    if case .previousCodeNotExpired(time: 42) = $0 { return true }; return false
}

let noContent: Result<BaseServerResponse, NetworkError> = HTTPResponseDecoder.decode(data: nil, statusCode: 204)
if case .failure = noContent { fatalError("Accept successful no-content mutations") }
let missingCatalog: Result<[Int], NetworkError> = HTTPResponseDecoder.decode(data: Data(), statusCode: 200)
expectFailure(missingCatalog, "An empty body is not a catalog") {
    if case .noData = $0 { return true }; return false
}
let nullCatalog: Result<[Int]?, NetworkError> = HTTPResponseDecoder.decode(data: Data("null".utf8), statusCode: 200)
guard case .success(nil) = nullCatalog else { fatalError("Preserve the backend's optional empty catalog") }
let catalog: Result<[Int], NetworkError> = HTTPResponseDecoder.decode(data: Data("[1,2]".utf8), statusCode: 200)
guard case .success(let values) = catalog else { fatalError("Decode successful catalog data") }
expect(values == [1, 2], "Preserve successful catalog contents")
let malformed: Result<[Int], NetworkError> = HTTPResponseDecoder.decode(data: Data("not json".utf8), statusCode: 200)
expectFailure(malformed, "Report malformed successful data") {
    if case .decodingError = $0 { return true }; return false
}
let notFound: Result<BaseServerResponse, NetworkError> = HTTPResponseDecoder.decode(data: Data(), statusCode: 404)
expectFailure(notFound, "Empty 404 must not count as successful authentication") {
    if case .unknown = $0 { return true }; return false
}

print("Network configuration and HTTP response tests passed.")


// Source rules retain joint conditions instead of inventing numerical minima.
let admissionJSON = #"""
{"min_class":null,"min_diploma_level":null,"is_bvi":true,"confirmation_subjects":null,"full_score_subjects":null,
 "source_relation":"school_conditions","admission_rule":{"admission_year":2026,"benefit_types":["bvi","100_points"],
 "values":{"grades":"11; исключения за 10 класс","program_scope":"Все, кроме 01.03.01","benefit":"БВИ при совместном выполнении условий"},
 "conditions":["Альтернативы применяются совместно"],"source_url":"https://example.org/official.pdf","location":{"page":2}}}
"""#.data(using: .utf8)!
let sourceBenefit = try JSONDecoder().decode(BenefitModel.self, from: admissionJSON)
expect(sourceBenefit.minClass == nil && sourceBenefit.minDiplomaLevel == nil, "Do not invent admission minima")
expect(sourceBenefit.sourceRelation == "school_conditions", "Keep school scope distinct")
expect(sourceBenefit.admissionRule?.benefitTypes.count == 2, "Keep both benefit types")
expect(sourceBenefit.admissionRule?.details.contains("Все, кроме 01.03.01") == true, "Display exclusions")
expect(sourceBenefit.admissionRule?.details.contains("Альтернативы применяются совместно") == true, "Display conditions")
let legacyJSON = #"{"min_class":10,"min_diploma_level":3,"is_bvi":true}"#.data(using: .utf8)!
let legacyBenefit = try JSONDecoder().decode(BenefitModel.self, from: legacyJSON)
expect(legacyBenefit.minClass == 10 && legacyBenefit.admissionRule == nil, "Continue decoding legacy benefits")
print("Admission response checks passed")


func decodeProgram(_ quantities: String) throws -> ProgramShortModel {
    let json = """
    {"program_id":1,"name":"Test","field":"01.03.01","required_subjects":[],"optional_subjects":[],"like":false,"link":"https://example.org",\(quantities)}
    """
    return try JSONDecoder().decode(ProgramShortModel.self, from: Data(json.utf8))
}
let unknownProgram = try decodeProgram(#""budget_places":null,"paid_places":null,"cost":null"#)
expect(unknownProgram.quantities.budgetText == "Нет данных", "Null budget places are unknown")
expect(unknownProgram.quantities.paidText == "Нет данных", "Null paid places are unknown")
expect(unknownProgram.quantities.costText == "Нет данных", "Unknown tuition has no currency suffix")
expect(unknownProgram.toViewModel().quantities.costText == "Нет данных", "List and detail agree")
let oldUnknownProgram = try decodeProgram(#""budget_places":0,"paid_places":0,"cost":0,"admission_metadata":{"places_known":false,"cost_known":false}"#)
expect(oldUnknownProgram.quantities.budgetText == "Нет данных", "Retain compatibility with old flagged placeholders")
expect(oldUnknownProgram.toViewModel().quantities.costText == "Нет данных", "Flags also apply to the list")
let knownZero = try decodeProgram(#""budget_places":0,"paid_places":12,"cost":0"#)
expect(knownZero.quantities.budgetText == "0", "Confirmed zero is not unknown")
expect(knownZero.quantities.paidText == "12", "Keep known places")
expect(knownZero.quantities.costText == "0 ₽/год", "Keep confirmed zero price")
let partiallyKnown = try decodeProgram(#""budget_places":25,"paid_places":null,"cost":350000"#)
expect(partiallyKnown.quantities.budgetText == "25" && partiallyKnown.quantities.paidText == "Нет данных", "Independent quantities")
expect(partiallyKnown.quantities.costText == "350 000 ₽/год", "Format confirmed tuition")
expect(ProgramQuantities.unknown.costText == "Нет данных", "Initial loading view has no fake zero")
print("Program quantity checks passed")

let semesterProgram = try decodeProgram(#""budget_places":52,"paid_places":35,"cost":265000,"admission_metadata":{"places_known":true,"cost_known":true,"cost_period":"semester","places_note":"Места на общий набор: 01.03.02","study_form":"очная","admission_year":2026,"quantity_notes":["Осенний семестр"],"quantity_evidence":{"cost":{"source_url":"https://example.org/fees.pdf","locator":"page=7"}}}"#)
expect(semesterProgram.quantities.costText == "265 000 ₽/семестр", "Semester fees are never labeled as annual")
expect(semesterProgram.toViewModel().quantities.costText == semesterProgram.quantities.costText, "List and detail retain the price period")
expect(semesterProgram.quantities.budgetText == "52", "Place counts have no presentation asterisk")
expect(semesterProgram.quantities.detailText.contains("Осенний семестр"), "Retain source qualifications")
expect(semesterProgram.toViewModel().admissionMetadata?.quantityEvidence?["cost"]?.sourceURL == "https://example.org/fees.pdf", "Source survives model conversion")
let budgetOnly = try decodeProgram(#""budget_places":36,"paid_places":0,"cost":null"#)
expect(budgetOnly.quantities.costText == "Нет платного набора", "No paid intake is not free tuition")

expect(ExternalWebLink.url("https://bmstu.ru")?.absoluteString == "https://bmstu.ru", "Do not duplicate URL schemes")
expect(ExternalWebLink.url("bmstu.ru/bachelor")?.absoluteString == "https://bmstu.ru/bachelor", "Support legacy scheme-less addresses")
expect(ExternalWebLink.url("http://example.org")?.scheme == "http", "Retain an explicit HTTP link")
expect(ExternalWebLink.url("") == nil && ExternalWebLink.url(nil) == nil, "Hide missing destinations")
expect(ExternalWebLink.url("javascript:alert(1)") == nil, "Only web destinations can open Safari")
expect(ExternalWebLink.url("https://user:password@example.org") == nil, "Do not open embedded credentials")
