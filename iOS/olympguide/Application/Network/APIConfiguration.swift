import Foundation

enum APIConfiguration {
    static let baseURL: URL = {
        guard let value = Bundle.main.object(forInfoDictionaryKey: "BASE_URL") as? String,
              let url = validatedBaseURL(value) else {
            fatalError("Set a valid HTTPS BASE_URL in Config/App.xcconfig.")
        }
        return url
    }()

    static func validatedBaseURL(_ value: String) -> URL? {
        guard !value.contains("$("),
              let components = URLComponents(string: value),
              components.scheme == "https",
              let host = components.host, !host.isEmpty,
              components.user == nil, components.password == nil,
              components.query == nil, components.fragment == nil else { return nil }
        return components.url
    }

    static func url(
        for endpoint: String,
        queryItems: [URLQueryItem]?,
        baseURL: URL = APIConfiguration.baseURL
    ) -> URL? {
        guard endpoint.hasPrefix("/"), !endpoint.hasPrefix("//"),
              !endpoint.contains("?"), !endpoint.contains("#"),
              var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            return nil
        }
        // Preserve /api/v1; resolving an absolute path against the URL drops it.
        let basePath = baseURL.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.path = (basePath.isEmpty ? "" : "/" + basePath) + endpoint
        components.queryItems = queryItems
        return components.url
    }
}
