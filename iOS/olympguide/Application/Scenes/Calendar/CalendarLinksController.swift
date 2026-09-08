import UIKit

final class CalendarLinksController: UITableViewController {
    private struct Program: Decodable { let program_id: Int; let name: String }
    private struct Catalog: Decodable { let olympiads: [PersonalOlympiad]; let programs: [Program] }
    private struct Link { let id: Int; let name: String; let program: Bool }
    private let event: PersonalCalendarEvent
    private var links: [Link] = []
    init(event:PersonalCalendarEvent) { self.event = event; super.init(style:.insetGrouped) }
    required init?(coder:NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func viewDidLoad() {
        super.viewDidLoad(); title = "Олимпиады и программы"
        NetworkService.shared.request(endpoint:"/personal/catalog",method:.get,queryItems:nil,body:nil,shouldCache:false) { [weak self] (r:Result<Catalog,NetworkError>) in
            guard let self else { return }
            switch r { case .success(let c):
                self.links = c.olympiads.filter{(self.event.olympiad_ids ?? []).contains($0.olympiad_id)}.map{Link(id:$0.olympiad_id,name:$0.name+" · "+$0.profile,program:false)}
                self.links += c.programs.filter{(self.event.program_ids ?? []).contains($0.program_id)}.map{Link(id:$0.program_id,name:$0.name,program:true)}
                self.tableView.reloadData()
            case .failure(let error): self.show(error.localizedDescription) }
        }
    }
    private func show(_ message:String) { let alert = UIAlertController(title:"Не удалось открыть",message:message,preferredStyle:.alert); alert.addAction(UIAlertAction(title:"Понятно",style:.default)); present(alert,animated:true) }
    override func tableView(_ tableView:UITableView,numberOfRowsInSection section:Int)->Int { links.count }
    override func tableView(_ tableView:UITableView,cellForRowAt indexPath:IndexPath)->UITableViewCell {
        let cell = UITableViewCell(style:.subtitle,reuseIdentifier:nil), link = links[indexPath.row]
        cell.textLabel?.text = link.name; cell.textLabel?.numberOfLines = 0; cell.detailTextLabel?.text = link.program ? "Программа" : "Олимпиада"; cell.accessoryType = .disclosureIndicator; return cell
    }
    override func tableView(_ tableView:UITableView,didSelectRowAt indexPath:IndexPath) {
        tableView.deselectRow(at:indexPath,animated:true); let link = links[indexPath.row]
        if link.program {
            NetworkService.shared.request(endpoint:"/program/\(link.id)",method:.get,queryItems:nil,body:nil) { [weak self] (r:Result<ProgramModel,NetworkError>) in
                switch r { case .success(let p): self?.navigationController?.pushViewController(ProgramAssembly.build(for:p),animated:true); case .failure(let error): self?.show(error.localizedDescription) }
            }
        } else {
            NetworkService.shared.request(endpoint:"/olympiad/\(link.id)",method:.get,queryItems:nil,body:nil) { [weak self] (r:Result<OlympiadModel,NetworkError>) in
                switch r { case .success(let o): self?.navigationController?.pushViewController(OlympiadAssembly.build(with:o),animated:true); case .failure(let error): self?.show(error.localizedDescription) }
            }
        }
    }
}

extension UIStackView {
    func addCalendarButton(olympiadID:Int? = nil, programID: @escaping () -> Int? = { nil }) {
        let button = UIButton(type:.system); button.setTitle("События и мой календарь →",for:.normal); button.titleLabel?.numberOfLines = 0
        button.addAction(UIAction { [weak self] _ in
            let calendar = PersonalCalendarViewController(olympiadID:olympiadID,programID:programID())
            self?.findViewController()?.navigationController?.pushViewController(calendar,animated:true)
        },for:.touchUpInside); addArrangedSubview(button)
    }
}
