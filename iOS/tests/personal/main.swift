import Foundation

func expect(_ condition: @autoclosure () -> Bool, _ message: String) { if !condition() { fatalError(message) } }
func decode<T: Decodable>(_ text: String, as: T.Type) throws -> T { try JSONDecoder().decode(T.self,from:Data(text.utf8)) }

let legacy = try decode(#"{"diploma_id":1,"class":11,"level":2,"olympiad":{"name":"Олимпиада","profile":"право","level":1}}"#,as:DiplomaModel.self)
expect(legacy.awardYear == nil && legacy.result == nil, "Legacy diploma facts stay unknown")
let current = try decode(#"{"diploma_id":1,"olympiad_id":23,"class":10,"level":1,"award_year":2026,"olympiad_year":"2025/2026","profile":"физика","result":"winner","olympiad":{"name":"Физтех","profile":"физика","level":1}}"#,as:DiplomaModel.self)
expect(current.awardYear == 2026 && current.olympiadYear == "2025/2026" && current.olympiadID == 23, "Keep diploma identity and distinct years")

var event = try decode(#"{"title":"Этап","kind":"final","season":"2026/2027","admission_year":null,"time_kind":"date_range","timezone":"Europe/Moscow","start_date":"2026-12-31","end_date":"2027-01-02","description":""}"#,as:PersonalCalendarEvent.self)
expect(event.includes("2027-01-02") && !event.includes("2027-01-03"), "Date range includes the final day")
event.time_kind = "undated"; event.start_date = nil; event.end_date = nil
expect(!event.includes("2026-09-08") && event.dateLabel == "Срок ещё не подтверждён", "No placeholder for an unknown date")
event.time_kind = "timed"; event.starts_at = "2026-09-08T23:30:00+03:00"; event.ends_at = "2026-09-09T00:00:00+03:00"
expect(event.dateKey == "2026-09-08" && !event.includes("2026-09-09"), "Timed range has an exclusive end")
event.timezone = "Asia/Vladivostok"; event.starts_at = "2026-09-09T00:30:00+10:00"; event.ends_at = nil
expect(event.dateKey == "2026-09-09", "Timed date uses the event's timezone")
event.starts_at = "2026-09-09T00:30:00.123+10:00"
expect(event.dateKey == "2026-09-09", "RFC3339 fractional seconds also retain the source date")

let payment = try decode(#"{"id":"test","name":"Стипендия","kind":"scholarship","amount_min":null,"amount_max":null,"currency":"RUB","frequency":"monthly","academic_year":null,"eligibility":"Условия","checked_on":"2026-09-08","scope":{"label":"Москва","program_names":[]},"sources":[{"url":"https://example.org/"}]}"#,as:Scholarship.self)
expect(payment.amountText == "Сумма не подтверждена", "Unknown money is not zero")
let applicant = try decode(#"{"admission_year":2027,"exams":[{"subject":"физика","score":85,"year":2026}]}"#,as:PersonalApplicant.self)
expect(applicant.admission_year == 2027 && applicant.exams[0].year == 2026, "Admission and exam years remain independent")
let recommendation = try decode(#"{"total":1,"message":"Документы проверяет вуз","items":[{"program_id":12,"name":"Программа","university":"Вуз","status":"manual_review","assessments":[{"diploma_id":1,"status":"manual_review","benefit":"bvi","reason":"Есть неразобранное исключение","checks":[],"source_rule":{"admission_year":2026,"benefit_types":["bvi"],"values":{"benefit":"БВИ при условии"},"conditions":["Исключение"],"source_url":"https://example.org/rules.pdf"}}]}]}"#,as:RecommendationsResponse.self)
expect(recommendation.items[0].assessments[0].source_rule.sourceURL.hasSuffix("rules.pdf"), "Manual result keeps its official evidence")
print("Personal models and calendar dates passed")
