/******************************************************************************
 * Acadza Studio — teacher portal hooks (localhost / production URL via config).
 ******************************************************************************/
#include "OBSBasic.hpp"
#include "OBSBasicControls.hpp"

#include <OBSApp.hpp>
#include <qt-wrappers.hpp>

#include <QDesktopServices>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QTimer>
#include <QUrl>

QString OBSBasic::AcadzaPortalBaseUrl() const
{
	const char *url = config_get_string(App()->GetUserConfig(), "Acadza", "PortalUrl");
	if (!url || !*url)
		return QStringLiteral("http://localhost:3000");
	QString q = QString::fromUtf8(url).trimmed();
	if (q.isEmpty())
		return QStringLiteral("http://localhost:3000");
	while (q.endsWith('/'))
		q.chop(1);
	return q;
}

void OBSBasic::AcadzaRefreshDriveStatus()
{
	if (!controlsDock)
		return;

	auto *controls = qobject_cast<OBSBasicControls *>(controlsDock->widget());
	if (!controls)
		return;

	const QUrl url(AcadzaPortalBaseUrl() + QStringLiteral("/api/obs/drive-status"));
	auto *nam = new QNetworkAccessManager(this);
	QNetworkReply *reply = nam->get(QNetworkRequest(url));

	connect(reply, &QNetworkReply::finished, this, [this, reply, nam, controls]() {
		const int status =
			reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
		const QByteArray body = reply->readAll();
		reply->deleteLater();
		nam->deleteLater();

		bool connected = false;
		QString email;

		if (status >= 200 && status < 300) {
			const QJsonDocument doc = QJsonDocument::fromJson(body);
			const QJsonObject obj = doc.object();
			connected = obj.value(QStringLiteral("connected")).toBool(false);
			email = obj.value(QStringLiteral("email")).toString();
		}

		controls->UpdateAcadzaDriveStatus(connected, email);

		if (connected && acadzaDrivePollTimer)
			acadzaDrivePollTimer->stop();
	});
}

void OBSBasic::AcadzaConnectDrive()
{
	const QString base = AcadzaPortalBaseUrl();
	const QUrl signin(base + QStringLiteral("/api/auth/signin"));
	if (!QDesktopServices::openUrl(signin)) {
		OBSMessageBox::warning(this, QTStr("Acadza.ConnectDrive.OpenFail.Title"),
				       QTStr("Acadza.ConnectDrive.OpenFail.Text"));
		return;
	}

	if (!acadzaDrivePollTimer) {
		acadzaDrivePollTimer = new QTimer(this);
		acadzaDrivePollTimer->setInterval(3000);
		connect(acadzaDrivePollTimer, &QTimer::timeout, this,
			&OBSBasic::AcadzaRefreshDriveStatus);
	}
	acadzaDrivePollTimer->start();
	AcadzaRefreshDriveStatus();
}

void OBSBasic::AcadzaEndClass()
{
	if (!outputHandler || !outputHandler->RecordingActive()) {
		OBSMessageBox::information(this, QTStr("Acadza.EndClass.NoRecording.Title"),
					   QTStr("Acadza.EndClass.NoRecording.Text"));
		return;
	}

	const QString base = AcadzaPortalBaseUrl();
	const QMessageBox::StandardButton button = OBSMessageBox::question(
		this, QTStr("Acadza.EndClass.Confirm.Title"),
		QTStr("Acadza.EndClass.Confirm.Text").arg(base),
		QMessageBox::Yes | QMessageBox::No, QMessageBox::Yes);

	if (button != QMessageBox::Yes)
		return;

	acadzaPendingUploadAfterStop = true;
	StopRecording();
}
