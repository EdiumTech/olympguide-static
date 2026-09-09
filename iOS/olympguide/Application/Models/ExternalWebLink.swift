import Foundation

/// Visible link titles are independent of their destination.
enum ExternalWebLink {
    static func url(_ address: String?) -> URL? {
        guard let text = address?.trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty else { return nil }
        let candidate = text.contains(":") ? text : "https://" + text
        guard let url = URL(string: candidate), let host = url.host, !host.isEmpty,
              ["https", "http"].contains(url.scheme?.lowercased() ?? ""),
              url.user == nil, url.password == nil else { return nil }
        return url
    }
}
