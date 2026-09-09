import UIKit
import SafariServices

final class PersonalCalendarViewController:UITableViewController {
    static let statuses=[("planned","В планах"),("registered","Зарегистрирован"),("participating","Участвую"),("completed","Завершено"),("skipped","Пропускаю")]
    static let kinds=[("registration_open","Начало регистрации"),("registration_close","Окончание регистрации"),("qualifying","Отборочный этап"),("final","Заключительный этап"),("results","Результаты"),("appeal","Апелляция"),("documents_open","Начало подачи документов"),("documents_close","Окончание подачи документов"),("admission","Приёмная кампания"),("custom","Своё событие")]
    private let scope=UISegmentedControl(items:["Мой план","Каталог"])
    private let mode=UISegmentedControl(items:["Список","По датам"])
    private let datePicker=UIDatePicker()
    private let olympiadID:Int?
    private let programID:Int?
    private var requestVersion=0
    private var items:[PersonalCalendarItem]=[]
    private var rows:[PersonalCalendarItem]=[]
    private var kind="",status="",season=""
    init(olympiadID:Int?=nil,programID:Int?=nil){self.olympiadID=olympiadID;self.programID=programID;super.init(style:.insetGrouped);title="Мой календарь"}
    required init?(coder:NSCoder){fatalError("init(coder:) has not been implemented")}
    override func viewDidLoad(){
        super.viewDidLoad();scope.selectedSegmentIndex=(olympiadID != nil || programID != nil) ? 1 : 0;mode.selectedSegmentIndex=0
        scope.addTarget(self,action:#selector(load),for:.valueChanged);mode.addTarget(self,action:#selector(applyFilter),for:.valueChanged)
        datePicker.datePickerMode = .date;datePicker.preferredDatePickerStyle = .inline;datePicker.locale=Locale(identifier:"ru_RU");datePicker.addTarget(self,action:#selector(applyFilter),for:.valueChanged)
        navigationItem.rightBarButtonItems=[UIBarButtonItem(barButtonSystemItem:.add,target:self,action:#selector(addCustom)),UIBarButtonItem(title:"Фильтры",style:.plain,target:self,action:#selector(filters))]
        refreshControl=UIRefreshControl();refreshControl?.addTarget(self,action:#selector(load),for:.valueChanged);load()
    }
    override func viewDidLayoutSubviews(){super.viewDidLayoutSubviews();resizeHeader()}
    private func resizeHeader(){guard let header=tableView.tableHeaderView else{return};let h=header.systemLayoutSizeFitting(CGSize(width:tableView.bounds.width-32,height:0),withHorizontalFittingPriority:.required,verticalFittingPriority:.fittingSizeLevel).height+24;if abs(header.frame.height-h)>1{header.frame.size.height=h;tableView.tableHeaderView=header}}
    @objc private func load(){
        requestVersion += 1; let request = requestVersion
        NetworkService.shared.request(endpoint:scope.selectedSegmentIndex==0 ? "/user/calendar" : "/calendar/events",method:.get,queryItems:nil,body:nil,shouldCache:false){[weak self](result:Result<[PersonalCalendarItem],NetworkError>) in
            guard let self, request == self.requestVersion else{return};self.refreshControl?.endRefreshing()
            switch result {case .success(let items):self.items=items;self.applyFilter();case .failure(let error):self.items=[];self.applyFilter();self.message(error.localizedDescription+"\nВойдите в аккаунт в разделе «Профиль», чтобы сохранять личный план.")}
        }
    }
    private func message(_ text:String?){let label=UILabel();label.text=text;label.numberOfLines=0;label.textAlignment = .center;label.font = .preferredFont(forTextStyle:.body);tableView.backgroundView=text==nil ? nil : label}
    @objc private func applyFilter(){
        let day=PersonalCalendarEvent.day(datePicker.date,.current)
        rows=items.filter{ row in (kind.isEmpty || row.event.kind==kind)&&(status.isEmpty || row.status==status)&&(season.isEmpty || row.event.season==season)&&(olympiadID==nil || (row.event.olympiad_ids ?? []).contains(olympiadID!))&&(programID==nil || (row.event.program_ids ?? []).contains(programID!))&&(mode.selectedSegmentIndex==0 || row.event.includes(day)) }.sorted{$0.event.dateKey<$1.event.dateKey}
        let header=UIStackView(arrangedSubviews:[scope,mode]);header.axis = .vertical;header.spacing=12;header.isLayoutMarginsRelativeArrangement=true;header.layoutMargins=UIEdgeInsets(top:12,left:16,bottom:12,right:16)
        if mode.selectedSegmentIndex==1{header.addArrangedSubview(datePicker)}
        tableView.tableHeaderView=header;resizeHeader();message(rows.isEmpty ? "Событий по этим фильтрам нет. Откройте каталог или добавьте своё событие.":nil);tableView.reloadData()
    }
    @objc private func filters(){
        let form=PersonalFormController();form.title="Фильтры";form.loadViewIfNeeded()
        form.choice("kind","Вид события",[("","Все события")]+Self.kinds,kind);form.choice("status","Участие",[("","Любой статус")]+Self.statuses,status)
        form.field("season","Учебный год олимпиады (пусто — все)",season)
        form.save={[weak self,weak form] in guard let self,let form else{return};self.kind=form.value("kind");self.status=form.value("status");self.season=form.value("season");self.applyFilter();self.navigationController?.popViewController(animated:true)}
        navigationController?.pushViewController(form,animated:true)
    }
    override func tableView(_ tableView:UITableView,numberOfRowsInSection section:Int)->Int{rows.count}
    override func tableView(_ tableView:UITableView,cellForRowAt indexPath:IndexPath)->UITableViewCell{
        let item=rows[indexPath.row],cell=UITableViewCell(style:.subtitle,reuseIdentifier:nil);var c=cell.defaultContentConfiguration();c.text=item.event.title
        c.secondaryText=[item.event.dateLabel,item.event.timezone,item.event.season.isEmpty ? nil : "Сезон "+item.event.season,item.event.admission_year.map{"Приём \($0)"},item.status.flatMap{s in Self.statuses.first{$0.0==s}?.1},item.dates_changed==true ? "Данные источника обновились":nil,item.source_active==false ? "Событие снято с графика":nil].compactMap{$0}.joined(separator:"\n")
        c.textProperties.numberOfLines=0;c.secondaryTextProperties.numberOfLines=0;cell.contentConfiguration=c;cell.accessoryType = .disclosureIndicator;return cell
    }
    override func tableView(_ tableView:UITableView,didSelectRowAt indexPath:IndexPath){tableView.deselectRow(at:indexPath,animated:true);edit(rows[indexPath.row])}
    @objc private func addCustom(){edit(nil)}
    private func edit(_ item:PersonalCalendarItem?){
        let form=PersonalFormController();form.title=item?.event.title ?? "Своё событие";form.loadViewIfNeeded()
        let isCustom=item==nil || (item?.plan_id != nil && item?.event_id==nil)
        let zone=TimeZone(identifier:item?.event.timezone ?? "Europe/Moscow") ?? .current
        if isCustom{
            form.field("title","Название",item?.event.title ?? "")
            form.choice("kind","Вид события",Self.kinds,item?.event.kind ?? "custom")
            form.choice("time_kind","Дата",[("all_day","Весь день"),("timed","Точное время"),("date_range","Диапазон дат"),("undated","Ещё не объявлена")],item?.event.time_kind ?? "all_day")
            form.field("timezone","Часовой пояс",zone.identifier)
            form.choice("timed_end","Для точного времени: окончание",[("no","Только начало"),("yes","Указать окончание")],item?.event.ends_at == nil ? "no" : "yes")
            let f=DateFormatter();f.dateFormat="yyyy-MM-dd";f.timeZone=zone;f.locale=Locale(identifier:"en_US_POSIX")
            let start=item?.event.starts_at.flatMap(PersonalCalendarEvent.instant) ?? item?.event.start_date.flatMap{f.date(from:$0)} ?? Date()
            let end=item?.event.ends_at.flatMap(PersonalCalendarEvent.instant) ?? item?.event.end_date.flatMap{f.date(from:$0)} ?? start
            form.picker("start","Начало",.date,start,zone);form.picker("end","Окончание",.date,end,zone)
            form.field("description","Описание",item?.event.description ?? "");form.field("season","Учебный год олимпиады (необязательно)",item?.event.season ?? "")
            form.field("admission_year","Год поступления (необязательно)",item?.event.admission_year.map(String.init) ?? "",keyboard:.numberPad)
            form.change={[weak form] in guard let form else{return};let precision=form.value("time_kind");for p in form.pickers.values{p.datePickerMode=precision=="timed" ? .dateAndTime : .date;p.timeZone=TimeZone(identifier:form.value("timezone")) ?? .current;p.isHidden=precision=="undated"};form.pickers["end"]?.isHidden = !(precision=="date_range" || (precision=="timed" && form.value("timed_end")=="yes"))}
            form.change?()
        }else if let item{
            form.label(item.event.dateLabel+" · "+item.event.timezone);form.label(item.event.description)
            if item.dates_changed==true{form.label("Данные источника обновились. Статус и заметка сохранены.");form.choice("acknowledge","Подтверждение",[("no","Проверю позже"),("yes","Обновление проверено")],"no")}
            if item.source_active==false{form.label("Событие снято с опубликованного графика.")}
            if let url=item.event.source_url.flatMap(URL.init(string:)),url.scheme=="https"{let b=UIButton(type:.system);b.setTitle("Официальный источник",for:.normal);b.addAction(UIAction{[weak form] _ in form?.present(SFSafariViewController(url:url),animated:true)},for:.touchUpInside);form.stack.addArrangedSubview(b)}
            if !(item.event.olympiad_ids ?? []).isEmpty || !(item.event.program_ids ?? []).isEmpty {
                let links = UIButton(type:.system); links.setTitle("Связанные олимпиады и программы",for:.normal)
                links.addAction(UIAction { [weak form] _ in form?.navigationController?.pushViewController(CalendarLinksController(event:item.event),animated:true) },for:.touchUpInside)
                form.stack.addArrangedSubview(links)
            }
        }
        if item?.plan_id != nil{form.choice("status","Участие",Self.statuses,item?.status ?? "planned");form.field("note","Моя заметка",item?.note ?? "")}
        let clientKey=UUID().uuidString
        form.save={[weak self,weak form] in
            guard let self,let form else{return};var event:[String:Any]=[:]
            if isCustom{
                guard let zone=TimeZone(identifier:form.value("timezone")) else{form.showError("Проверьте часовой пояс");return}
                event=["title":form.value("title"),"kind":form.value("kind"),"time_kind":form.value("time_kind"),"timezone":zone.identifier,"description":form.value("description"),"season":form.value("season")]
                if !form.value("admission_year").isEmpty{guard let y=Int(form.value("admission_year"))else{form.showError("Проверьте год поступления");return};event["admission_year"]=y}
                let start=form.pickers["start"]!.date,end=form.pickers["end"]!.date
                switch form.value("time_kind"){
                case "timed":let f=ISO8601DateFormatter();f.timeZone=zone;event["starts_at"]=f.string(from:start);if form.value("timed_end")=="yes"{event["ends_at"]=f.string(from:end)}
                case "all_day":event["start_date"]=PersonalCalendarEvent.day(start,zone)
                case "date_range":event["start_date"]=PersonalCalendarEvent.day(start,zone);event["end_date"]=PersonalCalendarEvent.day(end,zone)
                default:break
                }
            }
            let done: () -> Void = { [weak self] in self?.navigationController?.popViewController(animated:true);self?.load() }
            if let id=item?.plan_id{var body:[String:Any]=["status":form.value("status"),"note":form.value("note"),"acknowledge":form.value("acknowledge")=="yes"];if isCustom{body["event"]=event};form.mutation("/user/calendar/\(id)",method:.put,body:body,done:done)}
            else if let id=item?.id{form.mutation("/user/calendar",method:.post,body:["event_id":id],done:done)}
            else{form.mutation("/user/calendar/custom",method:.post,body:["client_key":clientKey,"event":event],done:done)}
        }
        if let id=item?.plan_id{let b=UIButton(type:.system);b.setTitle("Удалить из моего плана",for:.normal);b.tintColor = .systemRed;b.addAction(UIAction{[weak self,weak form] _ in form?.mutation("/user/calendar/\(id)",method:.delete,body:[:]){self?.navigationController?.popViewController(animated:true);self?.load()}},for:.touchUpInside);form.stack.addArrangedSubview(b)}
        navigationController?.pushViewController(form,animated:true)
    }
}
