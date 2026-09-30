const imageInput = document.getElementById("imageInput");

const dropZone = document.getElementById("dropZone");

const previewContainer =
    document.getElementById("previewContainer");

const previewImage =
    document.getElementById("previewImage");

const analyzeButton =
    document.getElementById("analyzeButton");

const loading =
    document.getElementById("loading");

const emptyResult =
    document.getElementById("emptyResult");

const resultContent =
    document.getElementById("resultContent");

const analysisSection =
    document.getElementById("analysisSection");

const analysisImage =
    document.getElementById("analysisImage");

const tableSection =
    document.getElementById("tableSection");

const resultsTable =
    document.getElementById("resultsTable");

const printButton =
    document.getElementById("printButton");


let selectedFile = null;

let latestResult = null;


// ---------------------------------------------------------
// FILE SELECTION
// ---------------------------------------------------------

imageInput.addEventListener(
    "change",
    function (event) {

        const file =
            event.target.files[0];

        if (file) {
            selectImage(file);
        }

    }
);


// ---------------------------------------------------------
// DRAG & DROP
// ---------------------------------------------------------

dropZone.addEventListener(
    "dragover",
    function (event) {

        event.preventDefault();

        dropZone.classList.add(
            "dragover"
        );

    }
);


dropZone.addEventListener(
    "dragleave",
    function () {

        dropZone.classList.remove(
            "dragover"
        );

    }
);


dropZone.addEventListener(
    "drop",
    function (event) {

        event.preventDefault();

        dropZone.classList.remove(
            "dragover"
        );

        const file =
            event.dataTransfer.files[0];

        if (file) {
            selectImage(file);
        }

    }
);


// ---------------------------------------------------------
// SELECT IMAGE
// ---------------------------------------------------------

function selectImage(file) {

    const allowedTypes = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ];

    if (!allowedTypes.includes(file.type)) {

        alert(
            "Please select a JPG, PNG or WEBP image."
        );

        return;
    }


    if (file.size > 15 * 1024 * 1024) {

        alert(
            "Image must be smaller than 15 MB."
        );

        return;
    }


    selectedFile = file;


    const reader =
        new FileReader();


    reader.onload = function (event) {

        previewImage.src =
            event.target.result;

        previewContainer.classList.remove(
            "hidden"
        );

        dropZone.classList.add(
            "hidden"
        );

        analyzeButton.disabled = false;

    };


    reader.readAsDataURL(file);
}


// ---------------------------------------------------------
// ANALYZE
// ---------------------------------------------------------

analyzeButton.addEventListener(
    "click",
    async function () {

        if (!selectedFile) {
            return;
        }


        setLoading(true);


        const formData =
            new FormData();

        formData.append(
            "file",
            selectedFile
        );


        try {

            const response =
                await fetch(
                    "/api/analyze",
                    {
                        method: "POST",
                        body: formData
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.error ||
                    "Analysis failed"
                );

            }


            latestResult = data;

            renderResult(data);

        }

        catch (error) {

            console.error(error);

            alert(
                "Analysis failed: " +
                error.message
            );

        }

        finally {

            setLoading(false);

        }

    }
);


// ---------------------------------------------------------
// LOADING STATE
// ---------------------------------------------------------

function setLoading(isLoading) {

    if (isLoading) {

        analyzeButton.disabled = true;

        loading.classList.remove(
            "hidden"
        );

    }

    else {

        analyzeButton.disabled =
            !selectedFile;

        loading.classList.add(
            "hidden"
        );

    }
}


// ---------------------------------------------------------
// RENDER RESULT
// ---------------------------------------------------------

function renderResult(data) {

    emptyResult.classList.add(
        "hidden"
    );

    resultContent.classList.remove(
        "hidden"
    );


    document.getElementById(
        "batchGrade"
    ).textContent =
        data.batch_grade;


    document.getElementById(
        "onionCount"
    ).textContent =
        data.onion_count;


    document.getElementById(
        "avgSize"
    ).textContent =
        data.average_size_mm;


    document.getElementById(
        "avgDefect"
    ).textContent =
        data.average_defect_score;


    document.getElementById(
        "countA"
    ).textContent =
        data.grade_distribution.A;


    document.getElementById(
        "countB"
    ).textContent =
        data.grade_distribution.B;


    document.getElementById(
        "countURS"
    ).textContent =
        data.grade_distribution.URS;


    const total =
        Math.max(data.onion_count, 1);


    document.getElementById(
        "barA"
    ).style.width =
        (
            data.grade_distribution.A /
            total *
            100
        ) + "%";


    document.getElementById(
        "barB"
    ).style.width =
        (
            data.grade_distribution.B /
            total *
            100
        ) + "%";


    document.getElementById(
        "barURS"
    ).style.width =
        (
            data.grade_distribution.URS /
            total *
            100
        ) + "%";


    const description =
        document.getElementById(
            "gradeDescription"
        );


    if (data.batch_grade === "A") {

        description.textContent =
            "Majority of detected onions meet the prototype Grade A criteria.";

    }

    else if (data.batch_grade === "B") {

        description.textContent =
            "Batch contains a mixed quality distribution.";

    }

    else {

        description.textContent =
            "Batch contains a significant number of onions requiring rejection review.";

    }


    // Annotated image

    if (data.annotated_image) {

        analysisImage.src =
            data.annotated_image;

        analysisSection.classList.remove(
            "hidden"
        );

    }


    // Table

    renderTable(
        data.detections || []
    );


    tableSection.classList.remove(
        "hidden"
    );


    // Scroll toward results

    setTimeout(
        function () {

            resultContent.scrollIntoView({
                behavior: "smooth",
                block: "nearest"
            });

        },
        200
    );
}


// ---------------------------------------------------------
// TABLE
// ---------------------------------------------------------

function renderTable(detections) {

    resultsTable.innerHTML = "";


    detections.forEach(
        function (item, index) {

            const row =
                document.createElement(
                    "tr"
                );


            let gradeClass = "urs";

            if (item.grade === "A") {
                gradeClass = "a";
            }

            else if (item.grade === "B") {
                gradeClass = "b";
            }


            row.innerHTML = `
                <td>
                    ${index + 1}
                </td>

                <td>
                    ${item.size_mm} mm
                </td>

                <td>
                    ${item.defect_score}%
                </td>

                <td>
                    <span class="grade-pill ${gradeClass}">
                        ${item.grade}
                    </span>
                </td>

                <td>
                    ${item.confidence}%
                </td>
            `;


            resultsTable.appendChild(
                row
            );

        }
    );


    if (detections.length === 0) {

        resultsTable.innerHTML = `
            <tr>
                <td colspan="5" style="text-align:center">
                    No onions detected. Try a clearer tray image.
                </td>
            </tr>
        `;

    }
}


// ---------------------------------------------------------
// PRINT QUALITY SLIP
// ---------------------------------------------------------

printButton.addEventListener(
    "click",
    function () {

        if (!latestResult) {
            return;
        }


        const data =
            latestResult;


        const popup =
            window.open(
                "",
                "_blank"
            );


        popup.document.write(`
            <!DOCTYPE html>

            <html>

            <head>

                <title>
                    Digital Quality Slip
                </title>

                <style>

                    body {
                        font-family: Arial;
                        padding: 35px;
                        color: #17251d;
                    }

                    h1 {
                        color: #08743a;
                    }

                    .header {
                        display:flex;
                        justify-content:space-between;
                        border-bottom:2px solid #08743a;
                        padding-bottom:15px;
                    }

                    .grade {
                        font-size:55px;
                        font-weight:bold;
                        color:#08743a;
                    }

                    .stats {
                        display:grid;
                        grid-template-columns:
                            repeat(3,1fr);
                        gap:10px;
                        margin:25px 0;
                    }

                    .box {
                        padding:15px;
                        background:#f1f6f3;
                        border-radius:10px;
                    }

                    table {
                        width:100%;
                        border-collapse:collapse;
                    }

                    th, td {
                        padding:10px;
                        border-bottom:1px solid #ddd;
                        text-align:left;
                    }

                    .footer {
                        margin-top:40px;
                        color:#666;
                        font-size:12px;
                    }

                </style>

            </head>


            <body>

                <div class="header">

                    <div>

                        <h1>
                            🧅 ONION DETECT
                        </h1>

                        <p>
                            Digital Quality Slip
                        </p>

                    </div>

                    <div class="grade">
                        ${data.batch_grade}
                    </div>

                </div>


                <div class="stats">

                    <div class="box">
                        <strong>
                            Onions
                        </strong>

                        <br>

                        ${data.onion_count}
                    </div>


                    <div class="box">
                        <strong>
                            Average Size
                        </strong>

                        <br>

                        ${data.average_size_mm} mm
                    </div>


                    <div class="box">
                        <strong>
                            Average Defect
                        </strong>

                        <br>

                        ${data.average_defect_score}%
                    </div>

                </div>


                <h3>
                    Grade Distribution
                </h3>

                <p>
                    Grade A:
                    ${data.grade_distribution.A}
                </p>

                <p>
                    Grade B:
                    ${data.grade_distribution.B}
                </p>

                <p>
                    URS:
                    ${data.grade_distribution.URS}
                </p>


                <h3 style="margin-top:30px">
                    Inspection Details
                </h3>


                <table>

                    <thead>

                        <tr>
                            <th>#</th>
                            <th>Size</th>
                            <th>Defect</th>
                            <th>Grade</th>
                            <th>Confidence</th>
                        </tr>

                    </thead>

                    <tbody>

                        ${data.detections.map(
                            (item, index) => `
                                <tr>
                                    <td>
                                        ${index + 1}
                                    </td>

                                    <td>
                                        ${item.size_mm} mm
                                    </td>

                                    <td>
                                        ${item.defect_score}%
                                    </td>

                                    <td>
                                        ${item.grade}
                                    </td>

                                    <td>
                                        ${item.confidence}%
                                    </td>
                                </tr>
                            `
                        ).join("")}

                    </tbody>

                </table>


                <div class="footer">

                    Prototype quality assessment.
                    Measurements are computer-vision
                    estimates and should not be treated
                    as official certification.

                </div>

            </body>

            </html>
        `);


        popup.document.close();

        popup.focus();

        popup.print();

    }
);
