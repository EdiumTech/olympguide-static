import UIKit
import SafariServices

final class ScholarshipsViewController: UITableViewController {
    private let query: [URLQueryItem]
    private let universityID: Int?
    private let isProgramScope: Bool
    private var scholarships: [Scholarship] = []
    init(universityID: Int? = nil, programID: Int? = nil) {
        self.universityID = universityID
        self.isProgramScope = programID != nil
        query = [universityID.map { URLQueryItem(name: "university_id", value: String($0)) },
                 programID.map { URLQueryItem(name: "program_id", value: String($0)) }].compactMap { $0 }
        super.init(style: .insetGrouped)
        title = "Стипендии"
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func viewDidLoad() {
        super.viewDidLoad()
        if isProgramScope, let universityID {
            navigationItem.rightBarButtonItem = UIBarButtonItem(title: "Все выплаты вуза", primaryAction: UIAction { [weak self] _ in
                self?.navigationController?.pushViewController(ScholarshipsViewController(universityID: universityID), animated: true)
            })
        }
        refreshControl = UIRefreshControl()
        refreshControl?.addTarget(self, action: #selector(load), for: .valueChanged)
        load()
    }
    @objc private func load() {
        NetworkService.shared.request(endpoint: "/scholarships", method: .get, queryItems: query, body: nil,
                                      shouldCache: false) { [weak self] (result: Result<[Scholarship], NetworkError>) in
            guard let self else { return }
            self.refreshControl?.endRefreshing()
            switch result {
            case .success(let rows):
                self.scholarships = rows
                self.showMessage(rows.isEmpty ? "Применимость выплат к этой программе ещё не подтверждена. Посмотрите раздел стипендий на странице вуза." : nil)
                self.tableView.reloadData()
            case .failure:
                self.showMessage("Не удалось загрузить стипендии. Потяните список вниз, чтобы повторить.")
            }
        }
    }
    private func showMessage(_ message: String?) {
        let label = UILabel(); label.text = message; label.numberOfLines = 0; label.textAlignment = .center
        label.font = .preferredFont(forTextStyle: .body)
        tableView.backgroundView = message == nil ? nil : label
    }
    override func numberOfSections(in tableView: UITableView) -> Int { scholarships.count }
    override func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? { scholarships[section].name }
    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { 1 + scholarships[section].sources.count }
    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = UITableViewCell(style: .subtitle, reuseIdentifier: nil), s = scholarships[indexPath.section]
        var content = cell.defaultContentConfiguration()
        if indexPath.row == 0 {
            let kind = ["scholarship":"Стипендия", "grant":"Грант", "prize":"Разовая премия", "tuition_discount":"Скидка на обучение"][s.kind] ?? s.kind
            content.text = s.amountText
            let frequency = ["monthly":"Ежемесячно", "one_time":"Однократно", "semester":"За семестр", "annual":"За год", "tuition":"На обучение"][s.frequency] ?? s.frequency
            content.secondaryText = [kind, frequency, s.scope.label, s.academic_year ?? "Учебный год не подтверждён", s.eligibility,
                s.payment_period, s.renewal.map { "Продление: " + $0 }, s.restrictions,
                s.application.map { "Заявление: " + $0 }, "Совместимость: " + (s.compatibility ?? "не подтверждена"),
                s.notes, s.scope.program_names.isEmpty ? nil : "Программы: " + s.scope.program_names.joined(separator: "; "),
                "Проверено " + s.checked_on].compactMap { $0 }.joined(separator: "\n\n")
            cell.selectionStyle = .none
        } else {
            content.text = "Официальный источник"; content.secondaryText = s.sources[indexPath.row - 1].url
            cell.accessoryType = .disclosureIndicator
        }
        content.textProperties.numberOfLines = 0; content.secondaryTextProperties.numberOfLines = 0
        cell.contentConfiguration = content
        return cell
    }
    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        guard indexPath.row > 0, let url = URL(string: scholarships[indexPath.section].sources[indexPath.row-1].url), url.scheme == "https" else { return }
        present(SFSafariViewController(url: url), animated: true)
    }
}

extension UIStackView {
    func addScholarshipsButton(universityID: Int? = nil, program: @escaping () -> Int? = { nil }) {
        let button = UIClosureButton()
        if let previous = arrangedSubviews.last { setCustomSpacing(18, after: previous) }
        var configuration = UIButton.Configuration.tinted()
        configuration.title = "Стипендии и поддержка"
        configuration.image = UIImage(systemName: "rublesign.circle")
        configuration.imagePadding = 10
        configuration.contentInsets = NSDirectionalEdgeInsets(top: 14, leading: 14, bottom: 14, trailing: 14)
        configuration.cornerStyle = .medium
        button.configuration = configuration
        button.setTitleColor(.systemBlue, for: .normal)
        button.titleLabel?.font = .preferredFont(forTextStyle: .body)
        button.titleLabel?.numberOfLines = 0
        button.contentHorizontalAlignment = .left
        button.action = { [weak self] in
            self?.findViewController()?.navigationController?.pushViewController(
                ScholarshipsViewController(universityID: universityID, programID: program()), animated: true)
        }
        addArrangedSubview(button)
        setCustomSpacing(18, after: button)
    }
}
