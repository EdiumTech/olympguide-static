import UIKit
import SafariServices

class RecommendationsViewController: UITableViewController {
    static let statuses = [("eligible","Проверенные условия выполнены"),("confirmation_required","Нужно подтверждение ЕГЭ"),("ineligible","Условия не выполнены"),("manual_review","Недостаточно данных / ручная проверка")]
    static let benefits = [("bvi","БВИ"),("100_points","100 баллов"),("other","Другое преимущество")]
    var diploma: DiplomaModel?
    private var profile = PersonalApplicant(admission_year:nil,exams:[])
    private var rows: [RecommendedProgram] = []
    private var loadingPage = false
    private var total = 0, version = 0
    private var status = "", benefit = "", query = "", info = "Загружаем…"
    init(diploma: DiplomaModel? = nil) { self.diploma = diploma; super.init(style:.insetGrouped) }
    required init?(coder:NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func viewDidLoad() {
        super.viewDidLoad(); title = diploma == nil ? "Куда подходят дипломы" : "Проверка диплома"
        navigationItem.rightBarButtonItems = [UIBarButtonItem(title:"Год и ЕГЭ",style:.plain,target:self,action:#selector(editProfile)),UIBarButtonItem(title:"Фильтры",style:.plain,target:self,action:#selector(filters))]
        refreshControl = UIRefreshControl(); refreshControl?.addTarget(self,action:#selector(reload),for:.valueChanged)
    }
    override func viewWillAppear(_ animated:Bool) { super.viewWillAppear(animated); reload() }
    override func viewDidLayoutSubviews() { super.viewDidLayoutSubviews(); resizeHeader() }
    private func resizeHeader() {
        guard let header = tableView.tableHeaderView else { return }
        let size = header.systemLayoutSizeFitting(CGSize(width:tableView.bounds.width,height:0),withHorizontalFittingPriority:.required,verticalFittingPriority:.fittingSizeLevel)
        if abs(header.frame.height-size.height)>1 { header.frame.size.height = size.height; tableView.tableHeaderView = header }
    }
    private func header() {
        let stack = UIStackView(); stack.axis = .vertical; stack.spacing = 16; stack.isLayoutMarginsRelativeArrangement = true; stack.layoutMargins = UIEdgeInsets(top:20,left:20,bottom:20,right:20)
        let label = UILabel(); label.font = .preferredFont(forTextStyle:.body); label.numberOfLines = 0; label.text = info; stack.addArrangedSubview(label)
        if let diploma {
            let name = UILabel(); name.numberOfLines = 0; name.text = diploma.olympiad.name + "\n" + (diploma.profile ?? "Профиль не уточнён") + " · " + (diploma.awardYear.map(String.init) ?? "год не указан"); stack.addArrangedSubview(name)
            let edit = UIButton(type:.system); edit.setTitle("Уточнить сведения диплома",for:.normal); edit.addTarget(self,action:#selector(editDiploma),for:.touchUpInside); stack.addArrangedSubview(edit)
        }
        tableView.tableHeaderView = stack; resizeHeader()
    }
    @objc private func reload() {
        version += 1; loadingPage = false; let request = version; rows = []; total = 0; info = "Загружаем…"; header(); tableView.reloadData()
        navigationItem.rightBarButtonItems?.first?.isEnabled = false
        NetworkService.shared.request(endpoint:"/user/admission-profile",method:.get,queryItems:nil,body:nil,shouldCache:false) { [weak self] (r:Result<PersonalApplicant,NetworkError>) in
            guard let self, request == self.version else { return }
            switch r { case .success(let p): self.profile = p; self.navigationItem.rightBarButtonItems?.first?.isEnabled = true; self.loadPage(request:request)
            case .failure(let error): self.info = error.localizedDescription; self.header(); self.refreshControl?.endRefreshing() }
        }
        if let id = diploma?.id {
            NetworkService.shared.request(endpoint:"/user/diplomas/",method:.get,queryItems:nil,body:nil,shouldCache:false) { [weak self] (r:Result<[DiplomaModel],NetworkError>) in
                guard let self, request == self.version else { return }; if case .success(let diplomas) = r, let d = diplomas.first(where:{$0.id==id}) { self.diploma = d; self.header() }
            }
        }
    }
    private func loadPage(request:Int) {
        guard !loadingPage else { return }; loadingPage = true
        var queryItems = [URLQueryItem(name:"limit",value:"24"),URLQueryItem(name:"offset",value:String(rows.count)),URLQueryItem(name:"status",value:status),URLQueryItem(name:"benefit",value:benefit),URLQueryItem(name:"q",value:query)]
        if let id = diploma?.id { queryItems.append(URLQueryItem(name:"diploma_id",value:String(id))) }
        NetworkService.shared.request(endpoint:"/user/recommendations",method:.get,queryItems:queryItems,body:nil,shouldCache:false) { [weak self] (r:Result<RecommendationsResponse,NetworkError>) in
            guard let self, request == self.version else { return }; self.loadingPage = false; self.refreshControl?.endRefreshing()
            switch r { case .success(let response): self.rows += response.items; self.total = response.total; self.info = response.message + "\n\nНайдено программ: \(response.total)"
            case .failure(let error): self.info = error.localizedDescription }
            self.header(); self.tableView.reloadData()
        }
    }
    @objc private func editProfile() { navigationController?.pushViewController(ApplicantFormController(profile),animated:true) }
    @objc private func editDiploma() {
        guard let diploma else { return }; let form = PersonalFormController(); form.title = "Сведения диплома"
        DiplomaForm.configure(form,diploma:diploma) { [weak self] in self?.navigationController?.popViewController(animated:true) }
        navigationController?.pushViewController(form,animated:true)
    }
    @objc private func filters() {
        let form = PersonalFormController(); form.title = "Подбор программ"; form.loadViewIfNeeded()
        form.choice("status","Статус",[("","Все статусы")]+Self.statuses,status); form.choice("benefit","Преимущество",[("","Все преимущества")]+Self.benefits,benefit); form.field("query","Программа или вуз",query)
        form.save = { [weak self,weak form] in guard let self,let form else { return }; self.status = form.value("status"); self.benefit = form.value("benefit"); self.query = form.value("query"); self.navigationController?.popViewController(animated:true) }
        navigationController?.pushViewController(form,animated:true)
    }
    override func tableView(_ tableView:UITableView,numberOfRowsInSection section:Int)->Int { rows.count + (rows.count<total ? 1 : 0) }
    override func tableView(_ tableView:UITableView,cellForRowAt indexPath:IndexPath)->UITableViewCell {
        let cell = UITableViewCell(style:.subtitle,reuseIdentifier:nil)
        if indexPath.row == rows.count { cell.textLabel?.text = "Ещё программы"; return cell }
        let row = rows[indexPath.row]; cell.textLabel?.text = row.name; cell.textLabel?.numberOfLines = 0
        cell.detailTextLabel?.text = row.university + "\n" + (Self.statuses.first{$0.0==row.status}?.1 ?? row.status); cell.detailTextLabel?.numberOfLines = 0; cell.accessoryType = .disclosureIndicator; return cell
    }
    override func tableView(_ tableView:UITableView,didSelectRowAt indexPath:IndexPath) {
        tableView.deselectRow(at:indexPath,animated:true)
        if indexPath.row == rows.count { loadPage(request:version); return }
        let row = rows[indexPath.row], detail = PersonalFormController(); detail.title = row.name; detail.loadViewIfNeeded(); detail.navigationItem.rightBarButtonItem = nil
        detail.label(row.university)
        let open = UIButton(type:.system); open.setTitle("Открыть программу",for:.normal)
        open.addAction(UIAction { [weak detail] _ in
            NetworkService.shared.request(endpoint:"/program/\(row.program_id)",method:.get,queryItems:nil,body:nil) { (r:Result<ProgramModel,NetworkError>) in
                switch r { case .success(let program): detail?.navigationController?.pushViewController(ProgramAssembly.build(for:program),animated:true); case .failure(let error): detail?.showError(error.localizedDescription) }
            }
        },for:.touchUpInside); detail.stack.addArrangedSubview(open)
        for assessment in row.assessments {
            detail.label((Self.benefits.first{$0.0==assessment.benefit}?.1 ?? "Преимущество из источника") + " · " + (Self.statuses.first{$0.0==assessment.status}?.1 ?? assessment.status))
            detail.label(assessment.reason)
            for check in assessment.checks { let state = ["pass":"Выполнено","fail":"Не выполнено","pending":"Нужно подтверждение","unknown":"Нужна проверка"][check.state] ?? "Нужна проверка"; detail.label(check.condition + " · " + state + "\n" + check.detail) }
            detail.label(assessment.source_rule.details)
            if let url = URL(string:assessment.source_rule.sourceURL), url.scheme == "https" {
                let source = UIButton(type:.system); source.setTitle("Официальный источник · приём \(assessment.source_rule.admissionYear)",for:.normal)
                source.addAction(UIAction { [weak detail] _ in detail?.present(SFSafariViewController(url:url),animated:true) },for:.touchUpInside); detail.stack.addArrangedSubview(source)
            }
        }
        detail.label("Соответствие условиям льготы не означает гарантированное зачисление. Документы проверяет вуз.")
        navigationController?.pushViewController(detail,animated:true)
    }
}
