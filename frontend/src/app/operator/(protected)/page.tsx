import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function OperatorHomePage() {
  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">خوش آمدید</CardTitle>
          <CardDescription>
            با موفقیت وارد شدید. داشبورد کامل اپراتور (لیست و مدیریت
            درخواست‌های واحد شما) در فاز بعدی تکمیل می‌شود.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </main>
  );
}
