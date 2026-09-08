import Foundation

struct PersonalCalendarEvent: Codable {
    var title:String;var kind:String;var season:String;var admission_year:Int?
    var time_kind:String;var timezone:String;var start_date:String?;var end_date:String?
    var starts_at:String?;var ends_at:String?;var source_url:String?;var checked_on:String?
    var description:String;var olympiad_ids:[Int]?;var program_ids:[Int]?
    var dateLabel:String {
        switch time_kind {
        case "undated":return "Срок ещё не подтверждён"
        case "all_day":return (start_date ?? "")+" · время не указано"
        case "date_range":return (start_date ?? "")+" — "+(end_date ?? "")+" включительно"
        default:
            let f=DateFormatter();f.locale=Locale(identifier:"ru_RU");f.timeZone=TimeZone(identifier:timezone);f.dateStyle = .medium;f.timeStyle = .short
            let start=starts_at.flatMap(Self.instant).map{f.string(from:$0)} ?? "Неизвестно"
            return start+(ends_at.flatMap(Self.instant).map{" — "+f.string(from:$0)} ?? "")
        }
    }
    var dateKey:String {
        if let start_date {return start_date}
        guard let s=starts_at,let d=Self.instant(s) else{return "9999"}
        return Self.day(d,TimeZone(identifier:timezone) ?? .current)
    }
    static func day(_ date:Date,_ zone:TimeZone)->String{let f=DateFormatter();f.calendar=Calendar(identifier:.gregorian);f.locale=Locale(identifier:"en_US_POSIX");f.timeZone=zone;f.dateFormat="yyyy-MM-dd";return f.string(from:date)}
    static func instant(_ value:String)->Date? {
        let formatter=ISO8601DateFormatter()
        if let date=formatter.date(from:value) { return date }
        formatter.formatOptions=[.withInternetDateTime,.withFractionalSeconds]
        return formatter.date(from:value)
    }
    func includes(_ date:String)->Bool {
        if time_kind=="undated" {return false}
        var endKey=end_date ?? dateKey
        if let end=ends_at.flatMap(Self.instant) {
            var calendar=Calendar(identifier:.gregorian);calendar.timeZone=TimeZone(identifier:timezone) ?? .current
            let dayEnd=end == calendar.startOfDay(for:end) ? calendar.date(byAdding:.day,value:-1,to:end)! : end
            endKey=Self.day(dayEnd,calendar.timeZone)
        }
        return dateKey<=date && date<=endKey
    }
}
struct PersonalCalendarItem:Decodable {
    let id:String?;let plan_id:Int?;let event_id:String?;let event:PersonalCalendarEvent
    let status:String?;let note:String?;let dates_changed:Bool?;let source_active:Bool?
}
