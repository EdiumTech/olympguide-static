import Foundation

struct Scholarship: Decodable {
    let id: String
    let name: String
    let kind: String
    let amount_min: Double?
    let amount_max: Double?
    let currency: String
    let frequency: String
    let academic_year: String?
    let eligibility: String
    let renewal: String?
    let payment_period: String?
    let restrictions: String?
    let application: String?
    let compatibility: String?
    let notes: String?
    let checked_on: String
    let scope: Scope
    let sources: [Source]
    struct Scope: Decodable { let label: String; let program_names: [String] }
    struct Source: Decodable { let url: String }
    var amountText: String {
        guard let lo = amount_min, let hi = amount_max else { return "Сумма не подтверждена" }
        let formatter = NumberFormatter(); formatter.numberStyle = .decimal; formatter.locale = Locale(identifier: "ru_RU")
        let lower = formatter.string(from: NSNumber(value: lo)) ?? "\(lo)"
        let upper = formatter.string(from: NSNumber(value: hi)) ?? "\(hi)"
        let period = ["monthly":"в месяц", "one_time":"однократно", "semester":"за семестр", "annual":"за год", "tuition":"на обучение"][frequency] ?? frequency
        return "\(lower)\(lo == hi ? "" : "–" + upper) \(currency) \(period)"
    }
}
