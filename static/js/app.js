console.log("ProjectManager Loaded");
const API="http://127.0.0.1:5000";

function getToken(){
    return localStorage.getItem("token");
}
function authHeader(){
    return{
        "Content-Type":"application/json",
        "Authorization":"Bearer "+getToken()
    };
}
function tokenHeader(){
    return{
        "Authorization":"Bearer "+getToken()
    };
}
function register(){
    const username=document.getElementById("username").value.trim();
    const email=document.getElementById("email").value.trim();
    const password=document.getElementById("password").value.trim();
    if(!username||!email||!password){
        alert("Fill all fields");
        return;
    }
    fetch(API+"/register",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({username,email,password})
    })
    .then(res=>res.json())
    .then(data=>{
        if(data.token){
            localStorage.setItem("token",data.token);
            alert(data.message);
            location="/login";
        }else{
            alert(data.message);
        }
    })
    .catch(()=>{
        alert("Server Error");
    });
}

function login(){
    const email=document.getElementById("email").value.trim();
    const password=document.getElementById("password").value.trim();
    if(!email||!password){
        alert("Fill all fields");
        return;
    }
    fetch(API+"/login",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({email,password})
    })
    .then(res=>res.json())
    .then(data=>{
        if(data.token){
            localStorage.setItem("token",data.token);
            alert(data.message);
            location="/dashboard";
        }else{
            alert(data.message);
        }
    })
    .catch(()=>{
        alert("Server Error");
    });
}

function logout(){
    localStorage.removeItem("token");
    location="/login";
}

function checkLogin(){
    if(!getToken())
        location="/login";
}
function createProject(){
    const title=document.getElementById("title").value.trim();
    const description=document.getElementById("description").value.trim();
    if(!title||!description){
        alert("Fill all fields");
        return;
    }
    fetch(API+"/create_project",{
        method:"POST",
        headers:authHeader(),
        body:JSON.stringify({title,description})
    })
    .then(res=>res.json())
    .then(data=>{
        alert(data.message);
        if(data.projectid)
            location="/dashboard";
    })
    .catch(()=>{
        alert("Server Error");
    });
}

function getProjects(){
    fetch(API+"/get_projects",{
        method:"GET",
        headers:tokenHeader()
    })
    .then(res=>res.json())
    .then(data=>{
        const projects=data.projects||[];
        let html="";
        let total=0;
        let done=0;
        if(projects.length===0){
            html='<div class="empty"><h2>No Projects Found</h2><p>Create your first project</p></div>';
        }else{
            projects.forEach(project=>{
                total+=project.total_tasks||0;
                done+=project.done_tasks||0;
                html+=`
                <div class="project-card">
                    <h2>${project.title}</h2>
                    <p>${project.description}</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:${project.progress}"></div>
                    </div>
                    <p>${project.done_tasks}/${project.total_tasks} Tasks Completed</p>
                    <div class="action-buttons">
                        <button onclick="location='/add_task?projectid=${project.project_id}'">Add Task</button>
                        <button onclick="location='/project_progress?projectid=${project.project_id}'">Progress</button>
                        <button class="danger" onclick="deleteProject(${project.project_id})">Delete</button>
                    </div>
                    <div id="tasks-${project.project_id}" class="task-list"></div>
                </div>`;
            });
        }
        document.getElementById("projects").innerHTML=html;
        projects.forEach(project=>getTasks(project.project_id));
        if(document.getElementById("projectCount"))
            document.getElementById("projectCount").innerText=projects.length;
        if(document.getElementById("taskCount"))
            document.getElementById("taskCount").innerText=total;
        if(document.getElementById("doneCount"))
            document.getElementById("doneCount").innerText=done;
        if(document.getElementById("overallProgress"))
            document.getElementById("overallProgress").innerText=total?Math.round(done/total*100)+"%":"0%";
    })
    .catch(()=>{
        alert("Unable to load projects");
    });
}
function addTask(){
    const projectid=new URLSearchParams(location.search).get("projectid");
    const title=document.getElementById("title").value.trim();
    const status=document.getElementById("status").value;

    if(!title){
        alert("Enter task title");
        return;
    }

    fetch(API+"/add_task/"+projectid,{
        method:"POST",
        headers:authHeader(),
        body:JSON.stringify({title,status})
    })
    .then(res=>res.json())
    .then(data=>{
        alert(data.message);
        location="/dashboard";
    })
    .catch(()=>alert("Server Error"));
}

function getTasks(projectid){
    fetch(API+"/get_tasks/"+projectid,{
        headers:tokenHeader()
    })
    .then(res=>res.json())
    .then(data=>{
        let html="";
        let tasks=data.tasks||[];
        if(tasks.length===0){
            html=`<div class="empty"><h3>No Tasks Available</h3></div>`;
        }else{
            tasks.forEach(task=>{
                html+=`
                <div class="task-card">
                    <h4>${task.title}</h4>
                    <p>Status: <strong>${task.status}</strong></p>
                    <button onclick="updateTask(${task.taskid},'${task.title}','${task.status}')">Edit</button>
                    <button class="danger" onclick="deleteTask(${task.taskid})">Delete</button>
                </div>`;
            });
        }
        const box=document.getElementById("tasks-"+projectid);
        if(box) box.innerHTML=html;
    });
}

function updateTask(id,title,status){
    let newTitle=prompt("Task Title",title);
    if(newTitle===null) return;

    let newStatus=prompt("Pending / In-Progress / Done",status);
    if(newStatus===null) return;

    fetch(API+"/update_task/"+id,{
        method:"PUT",
        headers:authHeader(),
        body:JSON.stringify({
            title:newTitle,
            status:newStatus
        })
    })
    .then(res=>res.json())
    .then(data=>{
        alert(data.message);
        location.reload();
    });
}

function deleteTask(taskid){
    if(!confirm("Delete this task?")) return;

    fetch(API+"/delete_task/"+taskid,{
        method:"DELETE",
        headers:tokenHeader()
    })
    .then(res=>res.json())
    .then(data=>{
        alert(data.message);
        location.reload();
    });
}

function deleteProject(projectid){
    if(!confirm("Delete this project?")) return;

    fetch(API+"/delete_project/"+projectid,{
        method:"DELETE",
        headers:tokenHeader()
    })
    .then(res=>res.json())
    .then(data=>{
        alert(data.message);
        location.reload();
    });
}
function getProjectProgress(){
    const projectid=new URLSearchParams(location.search).get("projectid");

    fetch(API+"/project_progress/"+projectid,{
        headers:tokenHeader()
    })
    .then(res=>res.json())
    .then(data=>{
        document.getElementById("progress").innerHTML=`
        <div class="project-card">
            <h2>${data.title}</h2>
            <p><strong>Total Tasks:</strong> ${data.total_tasks}</p>
            <p><strong>Pending:</strong> ${data.pending}</p>
            <p><strong>In Progress:</strong> ${data.in_progress}</p>
            <p><strong>Completed:</strong> ${data.done}</p>

            <div class="progress-bar">
                <div class="progress-fill" style="width:${data.progress_pct}%"></div>
            </div>

            <p><strong>Progress:</strong> ${data.progress_pct}%</p>
        </div>`;
    })
    .catch(()=>alert("Unable to load project progress"));
}

function goCreateProject(){
    location="/create_project";
}

function goDashboard(){
    location="/dashboard";
}

function goAddTask(projectid){
    location="/add_task?projectid="+projectid;
}

function goProjectProgress(projectid){
    location="/project_progress?projectid="+projectid;
}

window.onload=function(){
    checkLogin();

    if(document.getElementById("projects")){
        getProjects();
    }

    if(document.getElementById("progress")){
        getProjectProgress();
    }
};
