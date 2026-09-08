import Foundation

enum HTTPResponseDecoder {
    static func decode<T: Decodable>(data: Data?, statusCode: Int) -> Result<T, NetworkError> {
        // Errors use a separate schema, regardless of the requested success model.
        guard (200...299).contains(statusCode) else {
            if statusCode >= 500 {
                return .failure(.internalServerError)
            }
            if statusCode == 401 {
                return .failure(.unauthorized)
            }
            if let data = data,
               let response = try? JSONDecoder().decode(BaseServerResponse.self, from: data),
               let error = NetworkError(
                serverType: response.type ?? "",
                time: response.time,
                message: response.message
               ) {
                return .failure(error)
            }
            return .failure(.unknown(message: "Сервер вернул ошибку HTTP \(statusCode)."))
        }

        guard let data = data, !data.isEmpty else {
            if let response = BaseServerResponse(message: nil, type: nil, time: nil, token: nil) as? T {
                return .success(response)
            }
            return .failure(.noData)
        }
        do {
            return .success(try JSONDecoder().decode(T.self, from: data))
        } catch {
            return .failure(.decodingError)
        }
    }
}
