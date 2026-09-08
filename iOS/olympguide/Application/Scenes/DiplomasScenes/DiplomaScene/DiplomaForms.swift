import UIKit

struct PersonalOlympiad: Decodable {
    let olympiad_id: Int; let name: String; let profile: String; let category: String
}
struct PersonalCatalog: Decodable { let olympiads: [PersonalOlympiad] }

final class PersonalOlympiadPicker: UITableViewController, UISearchResultsUpdating {
    var selected: ((PersonalOlympiad) -> Void)?
    private var all: [PersonalOlympiad] = [], rows: [PersonalOlympiad] = []
    private let search = UISearchController(searchResultsController: nil)
    override func viewDidLoad() {
        super.viewDidLoad(); title = "Олимпиада и профиль"
        search.searchResultsUpdater = self; search.obscuresBackgroundDuringPresentation = false
        navigationItem.searchController = search; definesPresentationContext = true
        NetworkService.shared.request(endpoint:"/personal/catalog",method:.get,queryItems:nil,body:nil,shouldCache:false) { [weak self] (r: Result<PersonalCatalog,NetworkError>) in
            guard let self else { return }
            switch r { case .success(let catalog): self.all = catalog.olympiads; self.updateSearchResults(for: self.search)
            case .failure(let error): let label = UILabel(); label.text = error.localizedDescription; label.numberOfLines = 0; self.tableView.backgroundView = label }
        }
    }
    func updateSearchResults(for searchController: UISearchController) {
        let q = searchController.searchBar.text ?? ""
        rows = all.filter { q.isEmpty || ($0.name + " " + $0.profile).localizedCaseInsensitiveContains(q) }; tableView.reloadData()
    }
    override func tableView(_ tableView:UITableView,numberOfRowsInSection section:Int)->Int { rows.count }
    override func tableView(_ tableView:UITableView,cellForRowAt indexPath:IndexPath)->UITableViewCell {
        let cell = UITableViewCell(style:.subtitle,reuseIdentifier:nil), o = rows[indexPath.row]
        cell.textLabel?.text = o.name; cell.textLabel?.numberOfLines = 0
        cell.detailTextLabel?.text = o.profile + " · " + (o.category == "rsosh" ? "Перечневая" : o.category == "vsosh" ? "ВсОШ" : "Международная")
        cell.detailTextLabel?.numberOfLines = 0; return cell
    }
    override func tableView(_ tableView:UITableView,didSelectRowAt indexPath:IndexPath) {
        selected?(rows[indexPath.row]); navigationController?.popViewController(animated:true)
    }
}

enum DiplomaForm {
    static func configure(_ form: PersonalFormController, diploma: DiplomaModel? = nil, olympiad: OlympiadModel? = nil, done: @escaping () -> Void) {
        form.loadViewIfNeeded()
        form.label("Укажите сведения с диплома. Год поступления задаётся отдельно в разделе «Год и ЕГЭ».")
        var olympiadID = diploma?.olympiadID ?? olympiad?.olympiadID
        let choose = UIButton(type:.system); choose.titleLabel?.numberOfLines = 0
        choose.setTitle(diploma?.olympiad.name ?? olympiad?.name ?? "Выбрать олимпиаду",for:.normal)
        choose.addAction(UIAction { [weak form,weak choose] _ in
            let picker = PersonalOlympiadPicker()
            picker.selected = { [weak form,weak choose] o in olympiadID = o.olympiad_id; choose?.setTitle(o.name + " · " + o.profile,for:.normal); form?.inputs["profile"]?.text = o.profile }
            form?.navigationController?.pushViewController(picker,animated:true)
        },for:.touchUpInside); form.stack.addArrangedSubview(choose)
        form.field("profile","Профиль на дипломе",diploma?.profile ?? olympiad?.profile ?? "")
        form.field("award_year","Год получения диплома",diploma?.awardYear.map(String.init) ?? "",keyboard:.numberPad)
        form.field("olympiad_year","Учебный год олимпиады, например 2025/2026",diploma?.olympiadYear ?? "")
        form.choice("class","Класс выполнения заданий",(1...11).map{(String($0),String($0))},String(diploma?.diplomaClass ?? 11))
        form.choice("result","Результат",[("","Не указан"),("winner","Победитель"),("prize_winner","Призёр"),("participant","Участник")],diploma?.result ?? "")
        form.choice("level","Степень диплома",[("1","I"),("2","II"),("3","III")],String(diploma?.level ?? 1))
        form.label("Неизвестные поля можно оставить пустыми. Для старого диплома уточните соответствие олимпиаде и профилю в новом каталоге.")
        form.save = { [weak form] in
            guard let form else { return }
            guard let id = olympiadID else { form.showError("Выберите олимпиаду и профиль"); return }
            var body: [String:Any] = ["olympiad_id":id,"class":Int(form.value("class")) ?? 11,"level":Int(form.value("level")) ?? 1]
            let year = form.value("award_year")
            if !year.isEmpty && Int(year) == nil { form.showError("Проверьте год диплома"); return }
            body["award_year"] = year.isEmpty ? NSNull() : Int(year)! as Any
            for key in ["profile","olympiad_year","result"] { body[key] = form.value(key).isEmpty ? NSNull() : form.value(key) as Any }
            let endpoint = diploma.map { "/user/diploma/\($0.id)/details" } ?? "/user/diploma/"
            form.mutation(endpoint,method:diploma == nil ? .post : .put,body:body,done:done)
        }
    }
}

final class ApplicantFormController: PersonalFormController {
    private let profile: PersonalApplicant
    private var examKeys: [String] = []
    private static let subjects = ["математика","информатика","физика","химия","биология","русский язык","литература","история","обществознание","география","иностранный язык"]
    init(_ profile: PersonalApplicant) { self.profile = profile; super.init(nibName:nil,bundle:nil) }
    required init?(coder:NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func viewDidLoad() {
        super.viewDidLoad(); title = "Год поступления и ЕГЭ"
        field("admission_year","Год поступления",profile.admission_year.map(String.init) ?? "",keyboard:.numberPad)
        label("Правила 2026 не применяются к поступлению 2027. Указывайте полученные результаты ЕГЭ; документы и специальные основания проверяет вуз.")
        for exam in profile.exams { addExam(exam) }
        let button = UIButton(type:.system); button.setTitle("Добавить результат ЕГЭ",for:.normal)
        button.addAction(UIAction { [weak self] _ in self?.addExam(nil) },for:.touchUpInside); stack.addArrangedSubview(button)
        save = { [weak self] in
            guard let self else { return }
            guard let year = Int(self.value("admission_year")) else { self.showError("Укажите год поступления"); return }
            var exams: [[String:Any]] = []
            for key in self.examKeys {
                guard let score = Int(self.value(key+"score")), let examYear = Int(self.value(key+"year")) else { self.showError("Заполните баллы и год каждого ЕГЭ"); return }
                exams.append(["subject":self.value(key+"subject"),"score":score,"year":examYear])
            }
            self.mutation("/user/admission-profile",method:.put,body:["admission_year":year,"exams":exams]) { [weak self] in self?.navigationController?.popViewController(animated:true) }
        }
    }
    private func addExam(_ exam: PersonalExam?) {
        let key = UUID().uuidString; examKeys.append(key); let first = stack.arrangedSubviews.count
        choice(key+"subject","Предмет ЕГЭ",Self.subjects.map{($0,$0)},exam?.subject ?? "математика")
        field(key+"score","Баллы",exam.map{String($0.score)} ?? "",keyboard:.numberPad)
        field(key+"year","Год ЕГЭ",exam.map{String($0.year)} ?? "",keyboard:.numberPad)
        let remove = UIButton(type:.system); remove.setTitle("Убрать этот результат",for:.normal); remove.tintColor = .systemRed
        let views = Array(stack.arrangedSubviews[first...]); stack.addArrangedSubview(remove)
        remove.addAction(UIAction { [weak self,weak remove] _ in
            self?.examKeys.removeAll{$0==key}; for view in views where view !== remove { self?.stack.removeArrangedSubview(view); view.removeFromSuperview() }
            remove?.removeFromSuperview()
        },for:.touchUpInside)
    }
}
