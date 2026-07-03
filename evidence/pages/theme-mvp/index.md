---
title: Báo cáo hiệu quả kinh doanh
description: MVP kiểm thử theme report cho Evidence
max_width: 1520
hide_breadcrumbs: true
sidebar_position: 1
---

<!--
MVP REPORT THEME — EVIDENCE

Mục đích:
- Kiểm thử một hệ thống report có khả năng mở rộng thành dashboard.
- Bao phủ typography, narrative, KPI, filter, chart, table, disclosure và trạng thái.
- Dùng dữ liệu SQL giả lập, không phụ thuộc data source bên ngoài.
- Dùng semantic color classes của Evidence để kiểm thử light/dark theme.

Cách dùng:
1. Copy file này vào `pages/theme-mvp/+page.md` của một project Evidence.
2. Chạy project như bình thường. Các query bên dưới chạy trực tiếp trong Evidence.
3. Áp dụng theme qua `evidence.config.yaml`, `app.css` và `+layout.svelte`.
4. Kiểm tra ở các viewport: 390, 768, 1024, 1440 và 1920 px.
-->

```sql performance_base
with months as (
    select
        range as month_index,
        date '2025-01-01' + range * interval '1 month' as month
    from range(0, 18)
),
regions(region, region_factor, region_bias) as (
    values
        ('Miền Bắc', 1.12, 0.00),
        ('Miền Trung', 0.72, 0.65),
        ('Miền Nam', 1.28, 1.20),
        ('Mekong', 0.58, 1.80)
),
channels(channel, channel_factor, channel_bias) as (
    values
        ('Online', 1.25, 0.20),
        ('Cửa hàng', 1.00, 0.90),
        ('Đối tác', 0.62, 1.60)
),
generated as (
    select
        month,
        month_index,
        region,
        channel,
        channel_bias,
        round(
            (175000 + month_index * 9200)
            * region_factor
            * channel_factor
            * (1 + 0.065 * sin(month_index * 1.15 + region_bias + channel_bias)),
            0
        ) as revenue_usd0,
        round(
            (178000 + month_index * 9000)
            * region_factor
            * channel_factor,
            0
        ) as target_usd0,
        0.026
            + month_index * 0.00035
            + region_factor * 0.0015
            + channel_factor * 0.0018
            + 0.0012 * sin(month_index + channel_bias) as conversion_pct1,
        0.041
            - month_index * 0.00028
            + 0.0025 * cos(month_index + region_bias) as return_rate_pct1
    from months
    cross join regions
    cross join channels
),
calculated as (
    select
        *,
        greatest(
            1,
            round(revenue_usd0 / (82 + month_index * 0.7 + channel_bias * 5), 0)
        ) as orders_num0
    from generated
)
select
    month,
    month_index,
    region,
    channel,
    revenue_usd0,
    target_usd0,
    orders_num0,
    round(orders_num0 / conversion_pct1, 0) as sessions_num0,
    round(orders_num0 * return_rate_pct1, 0) as returns_num0,
    conversion_pct1,
    return_rate_pct1,
    revenue_usd0 / orders_num0 as aov_usd2
from calculated
order by month, region, channel
```

```sql region_options
select distinct region from ${performance_base} order by region
```

```sql channel_options
select distinct channel from ${performance_base} order by channel
```

<div class="mb-2 text-xs font-semibold uppercase tracking-widest text-primary">
    Monthly business review · Theme MVP
</div>

# Báo cáo hiệu quả kinh doanh

<div class="mb-8 flex flex-col gap-3 border-b border-base-300 pb-6 text-sm text-base-content-muted sm:flex-row sm:items-center sm:justify-between">
    <p class="m-0 max-w-3xl">
        Báo cáo mẫu dùng để kiểm chứng một hệ thống <strong>report-first</strong>: nội dung tường thuật
        là trục chính, dashboard widgets đóng vai trò bằng chứng và công cụ khám phá.
    </p>
    <div class="shrink-0"><LastRefreshed prefix="Cập nhật" /></div>
</div>

## Bộ lọc báo cáo

<div class="mb-8 rounded-xl border border-base-300 bg-base-200 p-4 sm:p-6">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DateRange
            data={performance_base}
            dates=month
            name=period
            title="Kỳ báo cáo"
        />

        <Dropdown
            data={region_options}
            name=regions
            value=region
            title="Khu vực"
            multiple
            selectAllByDefault
        />

        <Dropdown
            data={channel_options}
            name=channels
            value=channel
            title="Kênh bán"
            multiple
            selectAllByDefault
        />

        <ButtonGroup name=metric title="Chỉ số trên biểu đồ">
            <ButtonGroupItem valueLabel="Doanh thu" value="revenue" default />
            <ButtonGroupItem valueLabel="Đơn hàng" value="orders" />
            <ButtonGroupItem valueLabel="Chuyển đổi" value="conversion" />
        </ButtonGroup>
    </div>
</div>

```sql filtered_performance
select *
from ${performance_base}
where month between '${inputs.period.start}' and '${inputs.period.end}'
  and region in ${inputs.regions.value}
  and channel in ${inputs.channels.value}
```

```sql kpi_monthly
with monthly as (
    select
        month,
        sum(revenue_usd0) as revenue_usd0,
        sum(target_usd0) as target_usd0,
        sum(orders_num0) as orders_num0,
        sum(sessions_num0) as sessions_num0,
        sum(returns_num0) as returns_num0,
        sum(revenue_usd0) / nullif(sum(orders_num0), 0) as aov_usd2
    from ${filtered_performance}
    group by month
),
compared as (
    select
        *,
        revenue_usd0 / nullif(lag(revenue_usd0) over (order by month), 0) - 1
            as revenue_change_pct1,
        orders_num0 / nullif(lag(orders_num0) over (order by month), 0) - 1
            as orders_change_pct1,
        (orders_num0 / nullif(sessions_num0, 0))
            / nullif(lag(orders_num0 / nullif(sessions_num0, 0)) over (order by month), 0) - 1
            as conversion_change_pct1,
        (returns_num0 / nullif(orders_num0, 0))
            / nullif(lag(returns_num0 / nullif(orders_num0, 0)) over (order by month), 0) - 1
            as return_change_pct1
    from monthly
)
select
    *,
    orders_num0 / nullif(sessions_num0, 0) as conversion_pct1,
    returns_num0 / nullif(orders_num0, 0) as return_rate_pct1,
    revenue_usd0 / nullif(target_usd0, 0) as target_attainment_pct1
from compared
order by month desc
```

```sql metric_trend
select
    month,
    case
        when '${inputs.metric}' = 'orders' then sum(orders_num0)
        when '${inputs.metric}' = 'conversion'
            then sum(orders_num0) / nullif(sum(sessions_num0), 0)
        else sum(revenue_usd0)
    end as metric_value,
    case
        when '${inputs.metric}' = 'conversion' then null
        when '${inputs.metric}' = 'orders' then null
        else sum(target_usd0)
    end as target_value
from ${filtered_performance}
group by month
order by month
```

```sql region_summary
select
    region,
    sum(revenue_usd0) as revenue_usd0,
    sum(target_usd0) as target_usd0,
    sum(orders_num0) as orders_num0,
    sum(sessions_num0) as sessions_num0,
    sum(returns_num0) as returns_num0,
    sum(revenue_usd0) / nullif(sum(target_usd0), 0) as target_attainment_pct1,
    sum(orders_num0) / nullif(sum(sessions_num0), 0) as conversion_pct1,
    sum(returns_num0) / nullif(sum(orders_num0), 0) as return_rate_pct1,
    sum(revenue_usd0) / nullif(sum(orders_num0), 0) as aov_usd2
from ${filtered_performance}
group by region
order by revenue_usd0 desc
```

```sql channel_summary
select
    channel,
    sum(revenue_usd0) as revenue_usd0,
    sum(orders_num0) as orders_num0,
    sum(orders_num0) / nullif(sum(sessions_num0), 0) as conversion_pct1,
    sum(revenue_usd0) / nullif(sum(orders_num0), 0) as aov_usd2
from ${filtered_performance}
group by channel
order by revenue_usd0 desc
```

```sql monthly_region
select
    month,
    region,
    sum(revenue_usd0) as revenue_usd0
from ${filtered_performance}
group by month, region
order by month, region
```

```sql scatter_data
select
    region,
    channel,
    region || ' · ' || channel as segment,
    sum(sessions_num0) as sessions_num0,
    sum(revenue_usd0) as revenue_usd0,
    sum(orders_num0) / nullif(sum(sessions_num0), 0) as conversion_pct1,
    sum(revenue_usd0) / nullif(sum(orders_num0), 0) as aov_usd2
from ${filtered_performance}
group by region, channel
order by region, channel
```

```sql funnel_data
with totals as (
    select
        sum(sessions_num0) as sessions,
        sum(orders_num0) as orders
    from ${filtered_performance}
)
select 1 as stage_order, 'Phiên truy cập' as stage, sessions as customers from totals
union all
select 2, 'Xem sản phẩm', round(sessions * 0.64, 0) from totals
union all
select 3, 'Thêm vào giỏ', round(sessions * 0.14, 0) from totals
union all
select 4, 'Bắt đầu thanh toán', round(sessions * 0.065, 0) from totals
union all
select 5, 'Hoàn tất đơn hàng', orders from totals
order by stage_order
```

```sql detail_table
select
    month,
    region,
    channel,
    sum(revenue_usd0) as revenue_usd0,
    sum(target_usd0) as target_usd0,
    sum(revenue_usd0) / nullif(sum(target_usd0), 0) as target_attainment_pct1,
    sum(orders_num0) as orders_num0,
    sum(orders_num0) / nullif(sum(sessions_num0), 0) as conversion_pct1,
    sum(returns_num0) / nullif(sum(orders_num0), 0) as return_rate_pct1,
    sum(revenue_usd0) / nullif(sum(orders_num0), 0) as aov_usd2
from ${filtered_performance}
group by month, region, channel
order by month desc, revenue_usd0 desc
```

```sql region_sparklines
select
    region,
    sum(monthly_revenue) as revenue_usd0,
    array_agg(
        {'month': month, 'revenue': monthly_revenue}
        order by month
    ) as revenue_trend
from (
    select
        region,
        month,
        sum(revenue_usd0) as monthly_revenue
    from ${filtered_performance}
    group by region, month
)
group by region
order by revenue_usd0 desc
```

## Tóm tắt điều hành

Trong tháng gần nhất, doanh thu đạt **<Value data={kpi_monthly} column=revenue_usd0 />**,
tương đương **<Value data={kpi_monthly} column=target_attainment_pct1 />** kế hoạch. Tỷ lệ chuyển
đổi là **<Value data={kpi_monthly} column=conversion_pct1 />**, trong khi tỷ lệ hoàn trả ở mức
**<Value data={kpi_monthly} column=return_rate_pct1 />**.

{#if kpi_monthly[0].target_attainment_pct1 >= 1}
    <Alert status="success">
        Doanh thu tháng gần nhất đã đạt kế hoạch. Phần phân tích bên dưới cho biết khu vực và kênh
        nào đóng góp nhiều nhất vào kết quả này.
    </Alert>
{:else if kpi_monthly[0].target_attainment_pct1 >= 0.9}
    <Alert status="warning">
        Doanh thu đang ở gần ngưỡng kế hoạch nhưng chưa đạt mục tiêu. Cần ưu tiên các phân khúc có
        lượng truy cập cao và tỷ lệ chuyển đổi dưới trung bình.
    </Alert>
{:else}
    <Alert status="danger">
        Doanh thu thấp hơn đáng kể so với kế hoạch. Cần kiểm tra đồng thời traffic, conversion và
        giá trị đơn hàng thay vì chỉ tăng ngân sách acquisition.
    </Alert>
{/if}

### Các chỉ số chính

<Grid cols=4 gapSize=md>
    <div class="rounded-xl border border-base-300 bg-base-100 p-5">
        <BigValue
            data={kpi_monthly}
            value=revenue_usd0
            title="Doanh thu"
            description="Doanh thu ghi nhận trong tháng gần nhất của kỳ đã chọn"
            comparison=revenue_change_pct1
            comparisonTitle="so với tháng trước"
            sparkline=month
            sparklineType=area
            minWidth="100%"
            maxWidth="100%"
        />
    </div>

    <div class="rounded-xl border border-base-300 bg-base-100 p-5">
        <BigValue
            data={kpi_monthly}
            value=orders_num0
            title="Đơn hàng"
            comparison=orders_change_pct1
            comparisonTitle="so với tháng trước"
            sparkline=month
            sparklineType=bar
            minWidth="100%"
            maxWidth="100%"
        />
    </div>

    <div class="rounded-xl border border-base-300 bg-base-100 p-5">
        <BigValue
            data={kpi_monthly}
            value=conversion_pct1
            title="Tỷ lệ chuyển đổi"
            comparison=conversion_change_pct1
            comparisonTitle="so với tháng trước"
            sparkline=month
            minWidth="100%"
            maxWidth="100%"
        />
    </div>

    <div class="rounded-xl border border-base-300 bg-base-100 p-5">
        <BigValue
            data={kpi_monthly}
            value=return_rate_pct1
            title="Tỷ lệ hoàn trả"
            comparison=return_change_pct1
            comparisonTitle="so với tháng trước"
            sparkline=month
            downIsGood=true
            minWidth="100%"
            maxWidth="100%"
        />
    </div>
</Grid>

## Diễn biến và đóng góp

<div class="grid grid-cols-1 gap-6 xl:grid-cols-12">
    <section class="rounded-xl border border-base-300 bg-base-100 p-4 sm:p-6 xl:col-span-8">
        <div class="mb-2">
            <h3 class="m-0 text-base font-semibold text-base-heading">Diễn biến chỉ số theo tháng</h3>
            <p class="m-0 mt-1 text-sm text-base-content-muted">
                Thay đổi lựa chọn ở "Chỉ số trên biểu đồ" để kiểm thử state và format động.
            </p>
        </div>
        <LineChart
            data={metric_trend}
            x=month
            y=metric_value
            yFmt={inputs.metric === 'revenue' ? 'usd0' : inputs.metric === 'conversion' ? 'pct1' : 'num0'}
            chartAreaHeight=300
            xGridlines=false
            yGridlines=true
            legend=false
        />
    </section>

    <aside class="rounded-xl border border-base-300 bg-base-100 p-4 sm:p-6 xl:col-span-4">
        <div class="mb-2">
            <h3 class="m-0 text-base font-semibold text-base-heading">Doanh thu theo kênh</h3>
            <p class="m-0 mt-1 text-sm text-base-content-muted">So sánh đóng góp trong kỳ đã chọn.</p>
        </div>
        <BarChart
            data={channel_summary}
            x=channel
            y=revenue_usd0
            swapXY=true
            labels=true
            legend=false
            chartAreaHeight=300
        />
    </aside>
</div>

> **Nhận định cần kiểm thử:** đoạn narrative phải dễ đọc khi đặt giữa các visual. Khoảng cách trước
> và sau biểu đồ cần đủ rõ để người đọc nhận biết chuyển đổi giữa luận điểm và bằng chứng.

<div class="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
    <section class="rounded-xl border border-base-300 bg-base-100 p-4 sm:p-6">
        <div class="mb-2">
            <h3 class="m-0 text-base font-semibold text-base-heading">Cơ cấu doanh thu theo khu vực</h3>
            <p class="m-0 mt-1 text-sm text-base-content-muted">
                Stacked area dùng để kiểm thử palette nhiều series và dark mode.
            </p>
        </div>
        <AreaChart
            data={monthly_region}
            x=month
            y=revenue_usd0
            series=region
            chartAreaHeight=300
        />
    </section>

    <section class="rounded-xl border border-base-300 bg-base-100 p-4 sm:p-6">
        <div class="mb-2">
            <h3 class="m-0 text-base font-semibold text-base-heading">Quy mô và hiệu suất phân khúc</h3>
            <p class="m-0 mt-1 text-sm text-base-content-muted">
                Mỗi điểm là một tổ hợp khu vực–kênh; màu biểu thị khu vực.
            </p>
        </div>
        <ScatterPlot
            data={scatter_data}
            x=sessions_num0
            y=conversion_pct1
            size=revenue_usd0
            series=region
            tooltipTitle=segment
            chartAreaHeight=300
        />
    </section>
</div>

## Phân tích hành trình chuyển đổi

<div class="grid grid-cols-1 gap-6 xl:grid-cols-12">
    <section class="rounded-xl border border-base-300 bg-base-100 p-4 sm:p-6 xl:col-span-5">
        <FunnelChart
            data={funnel_data}
            nameCol=stage
            valueCol=customers
            title="Phễu chuyển đổi"
            subtitle="Từ phiên truy cập đến đơn hàng"
            showPercent=true
            legend=false
            funnelSort="descending"
        />
    </section>

    <section class="rounded-xl border border-base-300 bg-base-100 p-4 sm:p-6 xl:col-span-7">
<h3 class="m-0 text-base font-semibold text-base-heading">Cách đọc phễu</h3>

<p>Phễu giúp xác định vấn đề nằm ở <strong>acquisition</strong>, <strong>consideration</strong> hay
<strong>checkout</strong>. Không nên kết luận chỉ dựa trên tỷ lệ chuyển đổi tổng vì cùng một mức
conversion có thể được tạo ra bởi những pattern rơi rụng rất khác nhau.</p>

<Alert status="info">
Dữ liệu ở MVP này là dữ liệu mô phỏng. Trong triển khai thật, mỗi stage phải có định nghĩa
event, cửa sổ attribution và quy tắc deduplicate rõ ràng.
</Alert>

<Details title="Câu hỏi phân tích gợi ý">
<ul>
<li>Kênh nào tạo nhiều traffic nhưng ít phiên xem sản phẩm?</li>
<li>Khu vực nào có add-to-cart tốt nhưng checkout thấp?</li>
<li>Tỷ lệ hoàn trả có tăng ở nhóm có conversion cao không?</li>
<li>Thay đổi mix sản phẩm có làm AOV tăng nhưng số đơn giảm không?</li>
</ul>
</Details>
    </section>
</div>

## So sánh nhiều chế độ trình bày

<Tabs id="analysis-views">
    <Tab label="Khu vực">

        <BarChart
            data={region_summary}
            x=region
            y=revenue_usd0
            y2=target_usd0
            y2SeriesType=line
            labels=true
            chartAreaHeight=320
        />

    </Tab>

    <Tab label="Phân phối AOV">

        <Histogram
            data={detail_table}
            x=aov_usd2
            chartAreaHeight=320
        />

    </Tab>

    <Tab label="Bảng tóm tắt">

        <DataTable data={region_summary} rowLines=true>
            <Column id=region title="Khu vực" />
            <Column id=revenue_usd0 title="Doanh thu" contentType=bar align=left />
            <Column id=target_attainment_pct1 title="Đạt kế hoạch" contentType=colorscale colorScale={['negative','base-100','positive']} colorMid=1 />
            <Column id=conversion_pct1 title="Chuyển đổi" />
            <Column id=return_rate_pct1 title="Hoàn trả" redNegatives=false />
            <Column id=aov_usd2 title="AOV" />
        </DataTable>

    </Tab>
</Tabs>

## Chi tiết dữ liệu

Phần này kiểm thử bảng rộng, pagination, search, conditional formatting, data bars và sparkline. Trên
mobile, bảng phải có vùng scroll riêng thay vì làm toàn bộ trang tràn ngang.

<DataTable
    data={detail_table}
    rows=12
    search=true
    rowNumbers=true
    rowLines=true
>
    <Column id=month title="Tháng" fmt="mmm yyyy" />
    <Column id=region title="Khu vực" />
    <Column id=channel title="Kênh" />
    <Column id=revenue_usd0 title="Doanh thu" contentType=bar align=left />
    <Column id=target_attainment_pct1 title="Đạt kế hoạch" contentType=colorscale colorScale={['negative','base-100','positive']} colorMid=1 />
    <Column id=orders_num0 title="Đơn hàng" />
    <Column id=conversion_pct1 title="Chuyển đổi" />
    <Column id=return_rate_pct1 title="Hoàn trả" />
    <Column id=aov_usd2 title="AOV" />
</DataTable>

### Sparkline trong bảng

<DataTable data={region_sparklines} rowLines=true>
    <Column id=region title="Khu vực" />
    <Column id=revenue_usd0 title="Tổng doanh thu" contentType=bar align=left />
    <Column
        id=revenue_trend
        title="Xu hướng"
        contentType=sparkarea
        sparkX=month
        sparkY=revenue
        sparkYScale=false
        sparkColor=primary
    />
</DataTable>

## Định nghĩa và phương pháp

<Accordion single>
    <AccordionItem title="Doanh thu">

    Tổng giá trị đơn hàng được ghi nhận trong kỳ, trước khi trừ giá trị hoàn trả. Trong hệ thống thật,
    cần ghi rõ gross revenue hay net revenue và loại thuế được áp dụng.

    **Format:** tiền tệ, không có số thập phân.

    </AccordionItem>

    <AccordionItem title="Tỷ lệ chuyển đổi">

    Số đơn hàng hoàn tất chia cho số phiên truy cập hợp lệ. Bot traffic, internal traffic và phiên bị
    deduplicate phải bị loại trước khi tính.

    **Công thức:** `orders / sessions`.

    </AccordionItem>

    <AccordionItem title="Tỷ lệ hoàn trả">

    Số đơn hàng phát sinh hoàn trả chia cho số đơn hàng hoàn tất. Chỉ số này có độ trễ, vì vậy báo cáo
    production cần áp dụng observation window cố định.

    **Công thức:** `returned_orders / completed_orders`.

    </AccordionItem>

    <AccordionItem title="Mục tiêu">

    Mục tiêu tháng được phân bổ theo khu vực và kênh. MVP giả lập target tăng tuyến tính; production
    phải đọc từ bảng kế hoạch có version và thời điểm hiệu lực.

    </AccordionItem>
</Accordion>

<Details title="Nguồn dữ liệu và giới hạn">
<ul>
<li><strong>Nguồn:</strong> dữ liệu mô phỏng được tạo ngay trong query <code>performance_base</code>.</li>
<li><strong>Phạm vi:</strong> 18 tháng, 4 khu vực, 3 kênh bán.</li>
<li><strong>Giới hạn:</strong> không mô phỏng seasonality theo ngày, campaign attribution hoặc data latency.</li>
<li><strong>Mục đích:</strong> kiểm thử giao diện và interaction; không dùng để đưa ra quyết định kinh doanh.</li>
</ul>
</Details>

---

<div class="grid grid-cols-1 gap-4 py-2 text-sm text-base-content-muted sm:grid-cols-3">
    <div>
        <span class="block text-xs font-semibold uppercase tracking-wide">Owner</span>
        Analytics & Reporting
    </div>
    <div>
        <span class="block text-xs font-semibold uppercase tracking-wide">Cadence</span>
        Cập nhật hàng tháng
    </div>
    <div>
        <span class="block text-xs font-semibold uppercase tracking-wide">Trạng thái</span>
        MVP theme validation
    </div>
</div>
